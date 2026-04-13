from __future__ import annotations

import importlib.util
import os
import socket
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QLineEdit, QPushButton, QSlider, QSpinBox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "tools" / "PySide6TestApp" / "pyside6_effect_tester.py"


def load_module():
    spec = importlib.util.spec_from_file_location("release_effect_tester_module", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def process_events() -> None:
    app = get_app()
    app.processEvents()


class FakeBackend:
    def __init__(self) -> None:
        self.started = False
        self.closed = False
        self.applied_effects: list[tuple[str, str, str, dict[str, object]]] = []
        self.applied_presets: list[tuple[str, str]] = []
        self.effects = [
            {
                "id": "alpha_effect",
                "qualified_id": "pkg::alpha_effect",
                "title": "Alpha Effect",
                "source_id": "pkg",
                "tags": ["state"],
                "supported_layers": ["MAIN_LAYER", "STATE_LAYER"],
                "parameters": {
                    "color": {"type": "color", "default": "#112233", "description": ""},
                    "brightness": {"type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0, "description": ""},
                    "sparkle_count": {"type": "int", "default": 3, "minimum": 1, "description": ""},
                    "enabled": {"type": "bool", "default": True, "description": ""},
                    "mode": {
                        "type": "enum",
                        "default": "single",
                        "enum_values": ["single", "double"],
                        "description": "",
                    },
                    "palette": {"type": "color_list", "default": ["#AA0000", "#00AA00"], "description": ""},
                    "deadline_ts": {"type": "float", "default": None, "description": ""},
                    "custom_payload": {"type": "json", "default": "{}", "description": ""},
                },
            },
            {
                "id": "event_flash",
                "qualified_id": "pkg::event_flash",
                "title": "Event Flash",
                "source_id": "pkg",
                "tags": ["event"],
                "supported_layers": ["EVENT_LAYER"],
                "parameters": {
                    "duration_ms": {"type": "duration_ms", "default": 500, "minimum": 1, "description": ""}
                },
            },
        ]
        self.presets = {
            ("pkg", "alpha_effect"): [
                {"source_id": "pkg", "preset_id": "preset_red", "title": "Red", "params": {"color": "#FF0000"}},
                {"source_id": "pkg", "preset_id": "preset_green", "title": "Green", "params": {"color": "#00FF00"}},
                {"source_id": "pkg", "preset_id": "preset_blue", "title": "Blue", "params": {"color": "#0000FF"}},
                {"source_id": "pkg", "preset_id": "preset_plain", "title": "Plain", "params": {}},
            ],
            ("pkg", "event_flash"): [],
        }

    def start(self) -> dict[str, object]:
        self.started = True
        return {"host": "127.0.0.1", "port": 8765}

    def close(self) -> None:
        self.closed = True

    def list_effects(self) -> list[dict[str, object]]:
        return list(self.effects)

    def list_effect_presets(self, source_id: str, effect_id: str) -> list[dict[str, object]]:
        return list(self.presets[(source_id, effect_id)])

    def apply_effect(self, source_id: str, effect_id: str, target_layer: str, params: dict[str, object]) -> dict[str, object]:
        self.applied_effects.append((source_id, effect_id, target_layer, params))
        return {"ok": True}

    def apply_effect_preset(self, source_id: str, preset_id: str) -> dict[str, object]:
        self.applied_presets.append((source_id, preset_id))
        return {"ok": True}


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_subprocess_backend_can_start_fake_service_and_list_effects(tmp_path):
    module = load_module()
    port = _pick_free_port()
    service_script = tmp_path / "fake_service.py"
    service_script.write_text(
        """
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

argv = sys.argv[1:]
host = "127.0.0.1"
port = 8765
for index, value in enumerate(argv):
    if value == "--host":
        host = argv[index + 1]
    if value == "--port":
        port = int(argv[index + 1])

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def _write(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/v1/effects":
            self._write({"items": [{"id": "demo", "qualified_id": "pkg::demo", "source_id": "pkg", "title": "Demo", "supported_layers": ["MAIN_LAYER"], "tags": [], "parameters": {}}]})
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/v1/commands/shutdown":
            self._write({"ok": True})
            threading.Thread(target=httpd.shutdown, daemon=True).start()
            return
        self._write({"ok": True})

httpd = ThreadingHTTPServer((host, port), Handler)
print(json.dumps({"event": "service_binding", "host": host, "port": port}), flush=True)
httpd.serve_forever()
""",
        encoding="utf-8",
    )

    backend = module.ReleaseControllerBackend(
        sys.executable,
        host="127.0.0.1",
        requested_port=port,
        request_timeout=2.0,
        startup_timeout=5.0,
        service_arguments=[str(service_script)],
        working_directory=tmp_path,
    )
    binding = backend.start()
    try:
        assert binding["port"] == port
        items = backend.list_effects()
        assert items[0]["id"] == "demo"
    finally:
        backend.close()


def test_effect_tester_window_builds_dynamic_ui_and_couples_widgets(monkeypatch):
    module = load_module()
    get_app()
    backend = FakeBackend()
    monkeypatch.setattr(module.QMessageBox, "critical", staticmethod(lambda *args, **kwargs: None))

    window = module.EffectTesterWindow(backend)
    process_events()

    assert backend.started is True
    assert window.effect_combo.count() == 2
    assert window.apply_button.text() == "State setzen"

    preset_positions = [window.preset_layout.getItemPosition(index)[:2] for index in range(window.preset_layout.count())]
    assert preset_positions == [(0, 0), (0, 1), (0, 2), (1, 0)]

    preset_red = window.findChild(QPushButton, "preset-button-preset_red")
    assert preset_red is not None
    assert "#FF0000" in preset_red.styleSheet()

    color_line = window.findChild(QLineEdit, "param-color-text")
    color_button = window.findChild(QPushButton, "param-color-picker")
    assert color_line is not None and color_button is not None
    color_line.setText("#ABCDEF")
    process_events()
    assert "#ABCDEF" in color_button.styleSheet()

    brightness_spin = window.findChild(QSpinBox, "param-brightness-spin")
    brightness_slider = window.findChild(QSlider, "param-brightness-slider")
    assert brightness_spin is not None and brightness_slider is not None
    brightness_spin.setValue(75)
    process_events()
    assert brightness_slider.value() == 75

    sparkle_spin = window.findChild(QSpinBox, "param-sparkle_count-spin")
    sparkle_slider = window.findChild(QSlider, "param-sparkle_count-slider")
    assert sparkle_spin is not None and sparkle_slider is not None
    sparkle_slider.setValue(12)
    process_events()
    assert sparkle_spin.value() == 12

    enabled_checkbox = window.findChild(QCheckBox, "param-enabled-checkbox")
    enabled_button = window.findChild(QPushButton, "param-enabled-button")
    assert enabled_checkbox is not None and enabled_button is not None
    enabled_checkbox.setChecked(False)
    process_events()
    assert enabled_button.isChecked() is False
    assert enabled_button.text() == "Aus"

    mode_combo = window.findChild(QComboBox, "param-mode-combo")
    mode_line = window.findChild(QLineEdit, "param-mode-text")
    assert mode_combo is not None and mode_line is not None
    mode_combo.setCurrentText("double")
    process_events()
    assert mode_line.text() == "double"

    palette_first = window.findChild(QLineEdit, "param-palette-text-1")
    palette_second = window.findChild(QLineEdit, "param-palette-text-2")
    assert palette_first is not None and palette_second is not None
    palette_first.setText("#123456, 0x654321")
    process_events()
    assert palette_second.text() == "#123456, #654321"

    deadline_text = window.findChild(QLineEdit, "param-deadline_ts-text")
    assert deadline_text is not None
    deadline_text.setText("12.5")
    process_events()

    custom_payload = window.findChild(QLineEdit, "param-custom_payload-text-1")
    assert custom_payload is not None
    custom_payload.setText('{"demo": true}')
    process_events()

    preset_red.click()
    process_events()
    assert backend.applied_presets == [("pkg", "preset_red")]

    window.apply_button.click()
    process_events()
    assert backend.applied_effects == [
        (
            "pkg",
            "alpha_effect",
            "MAIN_LAYER",
            {
                "color": "#ABCDEF",
                "brightness": 0.75,
                "sparkle_count": 12,
                "enabled": False,
                "mode": "double",
                "palette": ["#123456", "#654321"],
                "deadline_ts": 12.5,
                "custom_payload": '{"demo": true}',
            },
        )
    ]

    window.effect_combo.setCurrentIndex(1)
    process_events()
    assert window.apply_button.text() == "Effekt einmalig abspielen"
    assert window.findChild(QSpinBox, "param-duration_ms-spin") is not None

    window.close()
    process_events()
    assert backend.closed is True