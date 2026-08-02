from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
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
        self.cleared_types: list[str] = []
        self.reload_count = 0
        self.effects = [
            {
                "id": "alpha_effect",
                "qualified_id": "pkg::alpha_effect",
                "title": "Alpha Effect",
                "source_id": "pkg",
                "type": "state",
                "tags": ["state"],
                "supported_layers": ["STATE_LAYER"],
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
                "type": "event",
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

    def reload_effects(self) -> list[dict[str, object]]:
        self.reload_count += 1
        return list(self.effects)

    def list_effect_presets(self, source_id: str, effect_id: str) -> list[dict[str, object]]:
        return list(self.presets[(source_id, effect_id)])

    def apply_effect(self, source_id: str, effect_id: str, target_layer: str, params: dict[str, object]) -> dict[str, object]:
        self.applied_effects.append((source_id, effect_id, target_layer, params))
        return {"ok": True}

    def apply_effect_preset(self, source_id: str, preset_id: str) -> dict[str, object]:
        self.applied_presets.append((source_id, preset_id))
        return {"ok": True}

    def clear_effect(self, definition_type: str) -> dict[str, object]:
        self.cleared_types.append(definition_type)
        return {"ok": True}


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_resolve_default_executable_prefers_dist_versioned_build(tmp_path):
    module = load_module()
    script_path = tmp_path / "tools" / "PySide6TestApp" / "pyside6_effect_tester.py"
    script_path.parent.mkdir(parents=True)
    script_path.write_text("# placeholder", encoding="utf-8")

    build_tools = tmp_path / "build-tools"
    build_tools.mkdir()
    (build_tools / "version.py").write_text('__version__ = "9.9.9"\n', encoding="utf-8")

    dist_exe = tmp_path / "dist" / "led_controller_service_9.9.9.exe"
    dist_exe.parent.mkdir()
    dist_exe.write_text("binary", encoding="utf-8")

    assert module.resolve_default_executable(script_path) == dist_exe.resolve()


def test_effect_studio_defaults_to_current_source_and_supports_schema_color_aliases():
    module = load_module()
    parser = module.build_arg_parser(MODULE_PATH)

    args = parser.parse_args([])

    assert args.service_exe is None
    assert args.use_device is True
    assert args.fps == 8.0
    assert module.normalize_color_value("rot") == "#FF0000"
    assert module.normalize_color_value("tuerkis") == "#00FFFF"


def test_effect_studio_refuses_a_second_hardware_controller(monkeypatch):
    module = load_module()
    controller = module.ServiceProcessController(
        sys.executable,
        use_device=True,
    )
    monkeypatch.setattr(
        module.ControllerHttpClient,
        "request_json",
        lambda self, method, path, payload=None: {
            "render_loop_running": True,
            "requested_output_mode": "device",
        },
    )

    with pytest.raises(RuntimeError, match="Hardwarezugriff laeuft bereits"):
        controller.start()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows job-object behavior")
def test_effect_studio_terminates_service_tree_when_owner_exits(tmp_path):
    marker = tmp_path / "service.pid"
    port = _pick_free_port()
    service_code = """
import json
import os
from pathlib import Path
import sys
import time

marker = Path(sys.argv[1])
port_index = sys.argv.index("--port") + 1
marker.write_text(str(os.getpid()), encoding="ascii")
print(json.dumps({"event": "service_binding", "host": "127.0.0.1", "port": int(sys.argv[port_index])}), flush=True)
time.sleep(60)
"""
    owner_code = f"""
import os
import runpy

namespace = runpy.run_path({str(MODULE_PATH)!r})
controller = namespace["ServiceProcessController"](
    {sys.executable!r},
    requested_port={port},
    startup_timeout=5.0,
    use_device=False,
    service_arguments=["-c", {service_code!r}, {str(marker)!r}],
    working_directory={str(tmp_path)!r},
)
controller.start()
os._exit(0)
"""

    subprocess.run(
        [sys.executable, "-c", owner_code],
        check=True,
        timeout=15.0,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    service_pid = int(marker.read_text(encoding="ascii"))

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        handle = kernel32.OpenProcess(0x1000, False, service_pid)
        if not handle:
            break
        kernel32.CloseHandle(handle)
        time.sleep(0.05)
    else:
        pytest.fail(f"Service process {service_pid} survived its owner process")


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
        if self.path == "/api/v1/ping":
            self._write({"ok": True})
            return
        if self.path == "/api/v2/states?details=true":
            self._write([{"id": "demo", "qualified_id": "pkg::demo", "source_id": "pkg", "type": "state", "overlay_mode": None, "title": "Demo", "tags": [], "parameters": {}, "runtime_inputs": {}}])
            return
        if self.path in {"/api/v2/overlays?details=true", "/api/v2/events?details=true"}:
            self._write([])
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
        use_device=False,
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


def test_effect_tester_window_builds_dynamic_ui_and_couples_widgets(monkeypatch, tmp_path):
    module = load_module()
    get_app()
    backend = FakeBackend()
    monkeypatch.setattr(module.QMessageBox, "critical", staticmethod(lambda *args, **kwargs: None))

    window = module.EffectTesterWindow(
        backend,
        effect_collections=[
            {
                "collection_id": "example-selection",
                "title": "Example Selection",
                "source_id": "pkg",
                "effect_ids": ["alpha_effect"],
            }
        ],
    )
    process_events()

    assert backend.started is True
    assert window.effect_list.count() == 2
    assert window.apply_button.text() == "State setzen"

    preset_positions = [window.preset_layout.getItemPosition(index)[:2] for index in range(window.preset_layout.count())]
    assert preset_positions == [(0, 0), (0, 1), (0, 2), (1, 0)]

    preset_red = window.findChild(QPushButton, "preset-button-preset_red")
    assert preset_red is not None
    assert "#FF0000" in preset_red.styleSheet()
    preset_red.click()
    process_events()
    assert backend.applied_presets == [("pkg", "preset_red")]

    color_line = window.findChild(QLineEdit, "param-color-text")
    color_button = window.findChild(QPushButton, "param-color-picker")
    assert color_line is not None and color_button is not None
    assert color_line.text() == "#FF0000"
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

    window.apply_button.click()
    process_events()
    assert backend.applied_effects == [
        (
            "pkg",
            "alpha_effect",
            "STATE_LAYER",
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

    window.draft_title_edit.setText("Listening Calm")
    window.draft_comment_edit.setPlainText("Kandidat fuer den ruhigen Listening-State")
    window.copy_draft_button.click()
    process_events()
    copied_draft = json.loads(QApplication.clipboard().text())
    assert copied_draft["format"] == "effect-preset-draft/1"
    assert copied_draft["effect"]["id"] == "alpha_effect"
    assert copied_draft["preset_draft"]["suggested_id"] == "listening_calm"
    assert copied_draft["preset_draft"]["comment"] == "Kandidat fuer den ruhigen Listening-State"
    assert copied_draft["preset_draft"]["params"]["brightness"] == 0.75

    exported_draft_path = tmp_path / "effect_preset_draft.json"
    monkeypatch.setattr(
        module.QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *_args, **_kwargs: (str(exported_draft_path), "JSON-Dateien (*.json)")),
    )
    try:
        window.export_draft_button.click()
        process_events()
        exported_draft = json.loads(exported_draft_path.read_text(encoding="utf-8"))
        assert exported_draft["preset_draft"]["params"] == copied_draft["preset_draft"]["params"]
        assert exported_draft["preset_draft"]["comment"] == copied_draft["preset_draft"]["comment"]
    finally:
        exported_draft_path.unlink(missing_ok=True)

    collection_index = window.package_filter.findData("collection:example-selection")
    assert collection_index >= 0
    window.package_filter.setCurrentIndex(collection_index)
    process_events()
    assert window.effect_list.count() == 1
    window.package_filter.setCurrentIndex(0)
    process_events()

    window.clear_button.click()
    process_events()
    assert backend.cleared_types == ["state"]

    window.search_edit.setText("event")
    process_events()
    assert window.effect_list.count() == 1
    window.search_edit.clear()
    process_events()
    window.type_filter.setCurrentIndex(3)
    process_events()
    assert window.effect_list.count() == 1

    window.effect_list.setCurrentRow(0)
    process_events()
    assert window.apply_button.text() == "Effekt einmalig abspielen"
    assert window.findChild(QSpinBox, "param-duration_ms-spin") is not None
    assert window.live_preview_checkbox.isEnabled() is False

    window.type_filter.setCurrentIndex(1)
    process_events()
    window.live_preview_checkbox.setChecked(True)
    brightness_spin = window.parameter_bindings["brightness"].primary_widget
    assert isinstance(brightness_spin, QSpinBox)
    brightness_spin.setValue(40)
    QTest.qWait(220)
    process_events()
    assert backend.applied_effects[-1][3]["brightness"] == 0.4

    window.reload_button.click()
    process_events()
    assert backend.reload_count == 1

    window.close()
    process_events()
    assert backend.closed is True


def test_effect_studio_loads_local_collection_and_builds_stable_draft(tmp_path):
    module = load_module()

    collection_path = tmp_path / "example-selection" / "set.json"
    collection_path.parent.mkdir(parents=True)
    collection_path.write_text(
        json.dumps(
            {
                "format": "effect-curation/1",
                "collection_id": "example-selection",
                "title": "Example Selection",
                "source_id": "default-effects",
                "effects": [
                    {"id": "direction_indicator"},
                    {"id": "soft_pulse"},
                ],
            }
        ),
        encoding="utf-8",
    )

    collections = module.load_effect_collections(tmp_path)
    assert len(collections) == 1
    assert collections[0]["collection_id"] == "example-selection"
    assert collections[0]["effect_ids"] == ["direction_indicator", "soft_pulse"]

    draft = module.build_preset_draft(
        {
            "id": "soft_pulse",
            "qualified_id": "default-effects::soft_pulse",
            "title": "Soft Pulse",
            "type": "state",
            "source_id": "default-effects",
            "package_id": "default-effects.soft_pulse",
        },
        {"color": "#123456", "speed": 0.8},
        title="Listening Calm",
        comment="Ruhiger Listening-State",
        created_at="2026-08-01T12:00:00+02:00",
    )
    assert draft == {
        "format": "effect-preset-draft/1",
        "created_at": "2026-08-01T12:00:00+02:00",
        "effect": {
            "id": "soft_pulse",
            "qualified_id": "default-effects::soft_pulse",
            "title": "Soft Pulse",
            "type": "state",
            "source_id": "default-effects",
            "package_id": "default-effects.soft_pulse",
        },
        "preset_draft": {
            "suggested_id": "listening_calm",
            "title": "Listening Calm",
            "comment": "Ruhiger Listening-State",
            "params": {"color": "#123456", "speed": 0.8},
        },
    }
