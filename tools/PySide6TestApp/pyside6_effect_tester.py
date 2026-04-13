from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib import error, request

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


UNSET = object()
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def _json_dumps(payload: dict[str, Any] | None) -> bytes | None:
    if payload is None:
        return None
    return json.dumps(payload, ensure_ascii=True).encode("utf-8")


def _contrast_text_color(color: str) -> str:
    qcolor = QColor(color)
    if not qcolor.isValid():
        return "#111111"
    luminance = (0.299 * qcolor.red()) + (0.587 * qcolor.green()) + (0.114 * qcolor.blue())
    return "#111111" if luminance > 186.0 else "#F8F8F8"


def normalize_color_value(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return f"#{value & 0xFFFFFF:06X}"

    text = str(value).strip()
    if not text:
        return None
    if text.lower().startswith("0x"):
        text = f"#{text[2:]}"
    qcolor = QColor(text)
    if not qcolor.isValid():
        return None
    return qcolor.name(QColor.NameFormat.HexRgb).upper()


def color_button_stylesheet(color: str | None) -> str:
    normalized = normalize_color_value(color)
    if normalized is None:
        return "QPushButton { background-color: #E0E0E0; color: #333333; }"
    return (
        "QPushButton {"
        f"background-color: {normalized};"
        f"color: {_contrast_text_color(normalized)};"
        "border: 1px solid #666666;"
        "padding: 4px 8px;"
        "}"
    )


def clear_layout(layout: QGridLayout | QVBoxLayout | QHBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        child_layout = item.layout()
        widget = item.widget()
        if child_layout is not None:
            clear_layout(child_layout)
        if widget is not None:
            widget.deleteLater()


def resolve_default_executable(script_path: Path) -> Path:
    candidates = [
        script_path.with_name("led_controller_service.exe"),
        script_path.parent / "led_controller_service.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def is_event_like(effect: dict[str, Any]) -> bool:
    tags = set(effect.get("tags", ()))
    layers = set(effect.get("supported_layers", ()))
    return "event" in tags or layers == {"EVENT_LAYER"}


def select_target_layer(effect: dict[str, Any]) -> str:
    layers = list(effect.get("supported_layers", ()))
    preferred = [
        "EVENT_LAYER",
        "MAIN_LAYER",
        "TEMP_OVERLAY_LAYER",
        "ONGOING_OVERLAY_LAYER",
        "STATE_LAYER",
        "BACKGROUND_STATE_LAYER",
    ]
    tags = set(effect.get("tags", ()))
    if "overlay" in tags:
        preferred = [
            "TEMP_OVERLAY_LAYER",
            "ONGOING_OVERLAY_LAYER",
            "MAIN_LAYER",
            "EVENT_LAYER",
            "STATE_LAYER",
            "BACKGROUND_STATE_LAYER",
        ]
    if "state" in tags:
        preferred = [
            "MAIN_LAYER",
            "STATE_LAYER",
            "BACKGROUND_STATE_LAYER",
            "TEMP_OVERLAY_LAYER",
            "ONGOING_OVERLAY_LAYER",
            "EVENT_LAYER",
        ]
    for name in preferred:
        if name in layers:
            return name
    return layers[0] if layers else "MAIN_LAYER"


def build_apply_label(effect: dict[str, Any]) -> str:
    tags = set(effect.get("tags", ()))
    if is_event_like(effect):
        return "Effekt einmalig abspielen"
    if "state" in tags:
        return "State setzen"
    return "Effekt setzen"


def format_effect_label(effect: dict[str, Any]) -> str:
    source_id = effect.get("source_id", "?")
    effect_id = effect.get("id", "?")
    title = effect.get("title") or effect_id
    return f"{title} ({source_id}::{effect_id})"


@dataclass(slots=True)
class NumericPresentation:
    minimum: float
    maximum: float
    step: float
    decimals: int
    ui_to_api: Callable[[float], Any]
    api_to_ui: Callable[[Any], float]
    use_slider: bool = True


def _safe_float(value: Any, fallback: float) -> float:
    try:
        if value is None:
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def infer_numeric_presentation(effect: dict[str, Any], name: str, meta: dict[str, Any]) -> NumericPresentation:
    param_type = str(meta.get("type", "")).strip().lower()
    minimum = meta.get("minimum")
    maximum = meta.get("maximum")
    default = meta.get("default")
    tags = set(effect.get("tags", ()))
    effect_layers = set(effect.get("supported_layers", ()))

    if name == "speed":
        return NumericPresentation(
            minimum=0.0,
            maximum=1000.0,
            step=10.0,
            decimals=0,
            ui_to_api=lambda value: round(value / 100.0, 4),
            api_to_ui=lambda value: _safe_float(value, 1.0) * 100.0,
        )

    if (
        name == "brightness"
        or name.endswith("brightness")
        or name in {"min_brightness", "duty_cycle", "sharpness"}
        or (minimum in {0, 0.0, None} and maximum in {1, 1.0})
    ):
        return NumericPresentation(
            minimum=0.0 if minimum is None else float(minimum) * 100.0,
            maximum=100.0 if maximum is None else float(maximum) * 100.0,
            step=1.0,
            decimals=0,
            ui_to_api=lambda value: round(value / 100.0, 4),
            api_to_ui=lambda value: _safe_float(value, 0.0) * 100.0,
        )

    if name == "sparkle_count":
        return NumericPresentation(
            minimum=0.0,
            maximum=30.0,
            step=1.0,
            decimals=0,
            ui_to_api=lambda value: int(round(value)),
            api_to_ui=lambda value: _safe_float(value, 0.0),
        )

    if name == "segment_length":
        return NumericPresentation(
            minimum=1.0,
            maximum=12.0,
            step=1.0,
            decimals=0,
            ui_to_api=lambda value: int(round(value)),
            api_to_ui=lambda value: _safe_float(value, 1.0),
        )

    if name == "target_led":
        return NumericPresentation(
            minimum=0.0,
            maximum=11.0,
            step=1.0,
            decimals=0,
            ui_to_api=lambda value: int(round(value)),
            api_to_ui=lambda value: _safe_float(value, 0.0),
        )

    if name.endswith("_deg") or "direction" in name:
        return NumericPresentation(
            minimum=0.0 if minimum is None else float(minimum),
            maximum=360.0 if maximum is None else float(maximum),
            step=1.0,
            decimals=0,
            ui_to_api=lambda value: round(value, 3),
            api_to_ui=lambda value: _safe_float(value, 0.0),
        )

    if param_type == "duration_ms" or name.endswith("_ms"):
        event_duration = name == "duration_ms" and ("event" in tags or effect_layers == {"EVENT_LAYER"})
        derived_max = 5000.0 if event_duration else 30000.0
        derived_step = 100.0 if event_duration else 1000.0
        if name in {"period_ms", "pause_ms"}:
            derived_max = 5000.0
            derived_step = 100.0
        if name in {"total_ms", "remaining_ms"}:
            derived_max = 30000.0
            derived_step = 1000.0
        return NumericPresentation(
            minimum=0.0 if minimum is None else float(minimum),
            maximum=derived_max if maximum is None else float(maximum),
            step=derived_step,
            decimals=0,
            ui_to_api=lambda value: int(round(value)),
            api_to_ui=lambda value: _safe_float(value, 0.0),
        )

    if minimum is not None and maximum is not None:
        low = float(minimum)
        high = float(maximum)
        span = abs(high - low)
        if param_type == "int":
            step = 1.0
            decimals = 0
        else:
            step = 0.01 if span <= 5 else 0.1 if span <= 50 else 1.0
            decimals = 2 if step < 0.1 else 1 if step < 1 else 0
        return NumericPresentation(
            minimum=low,
            maximum=high,
            step=step,
            decimals=decimals,
            ui_to_api=(lambda value: int(round(value))) if param_type == "int" else (lambda value: round(value, 4)),
            api_to_ui=lambda value: _safe_float(value, low),
        )

    if default is not None and minimum is not None:
        low = float(minimum)
        high = max(low + 1.0, float(default) * 4.0)
        step = 1.0 if param_type == "int" else 0.1
        return NumericPresentation(
            minimum=low,
            maximum=high,
            step=step,
            decimals=0 if param_type == "int" else 1,
            ui_to_api=(lambda value: int(round(value))) if param_type == "int" else (lambda value: round(value, 4)),
            api_to_ui=lambda value: _safe_float(value, low),
        )

    return NumericPresentation(
        minimum=0.0,
        maximum=100.0,
        step=1.0,
        decimals=0,
        ui_to_api=(lambda value: int(round(value))) if param_type == "int" else (lambda value: round(value, 4)),
        api_to_ui=lambda value: _safe_float(value, 0.0),
        use_slider=False,
    )


@dataclass(slots=True)
class ParameterBinding:
    name: str
    meta: dict[str, Any]
    primary_widget: QWidget
    secondary_widget: QWidget
    get_api_value: Callable[[], Any]
    set_api_value: Callable[[Any, bool], None]


class ControllerHttpClient:
    def __init__(self, host: str, port: int, *, timeout: float = 2.0) -> None:
        self.host = str(host)
        self.port = int(port)
        self.timeout = float(timeout)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        req = request.Request(
            f"{self.base_url}{path}",
            data=_json_dumps(payload),
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8") if exc.fp is not None else ""
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"Controller request failed: {exc}") from exc
        return {} if not raw else json.loads(raw)


class ServiceProcessController:
    def __init__(
        self,
        executable_path: str | Path,
        *,
        host: str = DEFAULT_HOST,
        requested_port: int = DEFAULT_PORT,
        port_pool: str | None = None,
        startup_timeout: float = 15.0,
        request_timeout: float = 2.0,
        use_device: bool = False,
        service_arguments: list[str] | None = None,
        working_directory: str | Path | None = None,
        on_output: Callable[[str], None] | None = None,
    ) -> None:
        self.executable_path = Path(executable_path).resolve()
        self.host = host
        self.requested_port = int(requested_port)
        self.port_pool = port_pool
        self.startup_timeout = float(startup_timeout)
        self.request_timeout = float(request_timeout)
        self.use_device = bool(use_device)
        self.service_arguments = list(service_arguments or [])
        self.working_directory = Path(working_directory).resolve() if working_directory is not None else self.executable_path.parent
        self.on_output = on_output

        self.process: subprocess.Popen[str] | None = None
        self.bound_host: str | None = None
        self.bound_port: int | None = None
        self.binding: dict[str, Any] | None = None
        self._binding_event = threading.Event()
        self._output_thread: threading.Thread | None = None
        self._recent_output: deque[str] = deque(maxlen=200)
        self._output_lock = threading.Lock()

    @property
    def runtime_state_file(self) -> Path:
        return self.working_directory / "runtime_state" / "active_service.json"

    def start(self) -> dict[str, Any]:
        if not self.executable_path.exists():
            raise FileNotFoundError(f"Service executable not found: {self.executable_path}")
        if self.process is not None and self.process.poll() is None:
            raise RuntimeError("Controller service is already running")

        command = [str(self.executable_path), *self.service_arguments]
        if not self.use_device:
            command.append("--no-device")
        command.extend(["serve", "--host", self.host, "--port", str(self.requested_port)])
        if self.port_pool:
            command.extend(["--port-pool", self.port_pool])

        self._binding_event.clear()
        self.binding = None
        self.bound_host = None
        self.bound_port = None
        self.process = subprocess.Popen(
            command,
            cwd=str(self.working_directory),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._output_thread = threading.Thread(target=self._consume_stdout, daemon=True)
        self._output_thread.start()

        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if self._binding_event.wait(timeout=0.1):
                return dict(self.binding or {})
            if self.process.poll() is not None:
                break
            fallback = self._read_active_service_file(expected_pid=self.process.pid)
            if fallback is not None:
                self._set_binding(fallback)
                return dict(self.binding or {})

        recent_output = "\n".join(self._recent_output)
        raise RuntimeError(f"Controller service did not bind in time. Recent output:\n{recent_output}")

    def close(self, *, force: bool = False, wait_timeout: float = 10.0) -> None:
        process = self.process
        if process is None:
            return
        if process.poll() is None and not force and self.bound_host and self.bound_port:
            try:
                client = ControllerHttpClient(self.bound_host, self.bound_port, timeout=self.request_timeout)
                client.request_json("POST", "/api/v1/commands/shutdown")
            except Exception:
                pass
        try:
            process.wait(timeout=wait_timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3.0)
        finally:
            self.process = None

    def _consume_stdout(self) -> None:
        process = self.process
        if process is None or process.stdout is None:
            return
        for raw_line in process.stdout:
            line = raw_line.rstrip("\r\n")
            with self._output_lock:
                self._recent_output.append(line)
            if self.on_output is not None:
                self.on_output(line)
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("event") == "service_binding":
                self._set_binding(payload)

    def _set_binding(self, payload: dict[str, Any]) -> None:
        self.binding = dict(payload)
        self.bound_host = str(payload["host"])
        self.bound_port = int(payload["port"])
        self._binding_event.set()

    def _read_active_service_file(self, *, expected_pid: int | None = None) -> dict[str, Any] | None:
        if not self.runtime_state_file.exists():
            return None
        try:
            payload = json.loads(self.runtime_state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        if expected_pid is not None:
            try:
                payload_pid = int(payload.get("pid", 0))
            except (TypeError, ValueError):
                return None
            if payload_pid != expected_pid:
                return None
        if payload.get("host") and payload.get("port"):
            return payload
        return None

    def recent_output(self) -> str:
        with self._output_lock:
            return "\n".join(self._recent_output)


class ReleaseControllerBackend:
    def __init__(
        self,
        executable_path: str | Path,
        *,
        host: str = DEFAULT_HOST,
        requested_port: int = DEFAULT_PORT,
        port_pool: str | None = None,
        startup_timeout: float = 15.0,
        request_timeout: float = 2.0,
        use_device: bool = True,
        service_arguments: list[str] | None = None,
        working_directory: str | Path | None = None,
    ) -> None:
        self.process_controller = ServiceProcessController(
            executable_path,
            host=host,
            requested_port=requested_port,
            port_pool=port_pool,
            startup_timeout=startup_timeout,
            request_timeout=request_timeout,
            use_device=use_device,
            service_arguments=service_arguments,
            working_directory=working_directory,
        )
        self.client: ControllerHttpClient | None = None

    def start(self) -> dict[str, Any]:
        binding = self.process_controller.start()
        self.client = ControllerHttpClient(binding["host"], int(binding["port"]), timeout=self.process_controller.request_timeout)
        self._wait_until_ready()
        return binding

    def close(self) -> None:
        self.process_controller.close()
        self.client = None

    def get_status(self) -> dict[str, Any]:
        return self._client().request_json("GET", "/api/v1/status")

    def _client(self) -> ControllerHttpClient:
        if self.client is None:
            raise RuntimeError("Backend is not started")
        return self.client

    def list_effects(self) -> list[dict[str, Any]]:
        return list(self._client().request_json("GET", "/api/v1/effects").get("items", ()))

    def list_effect_presets(self, source_id: str, effect_id: str) -> list[dict[str, Any]]:
        path = f"/api/v1/effects/{source_id}/{effect_id}/presets"
        return list(self._client().request_json("GET", path).get("items", ()))

    def apply_effect(self, source_id: str, effect_id: str, target_layer: str, params: dict[str, Any]) -> dict[str, Any]:
        path = f"/api/v1/effects/{source_id}/{effect_id}/apply"
        return self._client().request_json(
            "POST",
            path,
            {
                "target_layer": target_layer,
                "params": params,
                "replace_existing": True,
                "enqueue": False,
            },
        )

    def apply_effect_preset(self, source_id: str, preset_id: str) -> dict[str, Any]:
        return self._client().request_json("POST", f"/api/v1/effect-presets/{source_id}/{preset_id}/apply")

    def _wait_until_ready(self) -> None:
        deadline = time.monotonic() + self.process_controller.startup_timeout
        last_error: str | None = None
        while time.monotonic() < deadline:
            process = self.process_controller.process
            if process is not None and process.poll() is not None:
                recent_output = self.process_controller.recent_output()
                raise RuntimeError(
                    "Controller service terminated before the API became ready."
                    + (f" Recent output:\n{recent_output}" if recent_output else "")
                )
            try:
                self._client().request_json("GET", "/api/v1/ping")
                return
            except RuntimeError as exc:
                last_error = str(exc)
                time.sleep(0.1)

        recent_output = self.process_controller.recent_output()
        detail = last_error or "unknown startup error"
        if recent_output:
            detail = f"{detail}\nRecent output:\n{recent_output}"
        raise RuntimeError(f"Controller API did not become ready in time: {detail}")


class EffectTesterWindow(QMainWindow):
    def __init__(self, backend: Any) -> None:
        super().__init__()
        self.backend = backend
        self.effects: list[dict[str, Any]] = []
        self.effect_presets: dict[str, list[dict[str, Any]]] = {}
        self.parameter_bindings: dict[str, ParameterBinding] = {}
        self.current_effect: dict[str, Any] | None = None

        self.setWindowTitle("LED Controller Effect Tester")
        self.resize(980, 760)

        self.effect_combo = QComboBox()
        self.effect_combo.currentIndexChanged.connect(self._on_effect_changed)
        self.status_label = QLabel("Starte Service ...")
        self.status_label.setWordWrap(True)

        self.preset_group = QGroupBox("Presets")
        self.preset_layout = QGridLayout()
        self.preset_group.setLayout(self.preset_layout)

        self.parameter_group = QGroupBox("Freier Parameterbereich")
        self.parameter_layout = QGridLayout()
        self.parameter_group.setLayout(self.parameter_layout)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.addWidget(self.preset_group)
        scroll_layout.addWidget(self.parameter_group)
        scroll_layout.addStretch(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_content)

        container = QWidget()
        root_layout = QVBoxLayout(container)
        root_layout.addWidget(self.effect_combo)
        root_layout.addWidget(self.status_label)
        root_layout.addWidget(scroll_area)
        self.setCentralWidget(container)

        self._start_backend_and_load_effects()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        try:
            self.backend.close()
        finally:
            super().closeEvent(event)

    def _start_backend_and_load_effects(self) -> None:
        try:
            binding = self.backend.start()
            status = self.backend.get_status()
            self.status_label.setText(f"Service aktiv auf {binding['host']}:{binding['port']}")
            if status.get("fallback_active"):
                requested_output_mode = status.get("requested_output_mode") or "unbekannt"
                active_output_mode = status.get("output_mode") or "unbekannt"
                last_error = status.get("last_error") or "Kein Fehlertext verfuegbar."
                QMessageBox.warning(
                    self,
                    "Geraet nicht verfuegbar",
                    "Der Service laeuft, aber nicht auf dem Geraet.\n\n"
                    f"Angefordert: {requested_output_mode}\n"
                    f"Aktiv: {active_output_mode}\n"
                    f"Fehler: {last_error}",
                )
            self.effects = sorted(
                self.backend.list_effects(),
                key=lambda item: (item.get("source_id", ""), item.get("title", ""), item.get("id", "")),
            )
            self._populate_effects()
        except Exception as exc:
            self.effect_combo.setEnabled(False)
            self.status_label.setText(f"Service konnte nicht gestartet werden: {exc}")
            QMessageBox.critical(self, "Service-Start fehlgeschlagen", str(exc))

    def _populate_effects(self) -> None:
        with QSignalBlocker(self.effect_combo):
            self.effect_combo.clear()
            for effect in self.effects:
                self.effect_combo.addItem(format_effect_label(effect), effect["qualified_id"])
        if self.effects:
            self.effect_combo.setCurrentIndex(0)
            self._on_effect_changed(0)
        else:
            self.status_label.setText("Keine Effekte verfuegbar.")

    def _on_effect_changed(self, index: int) -> None:
        if index < 0 or index >= len(self.effects):
            self.current_effect = None
            self._render_empty_presets()
            self._render_empty_parameters()
            return
        effect = self.effects[index]

        self.current_effect = effect
        self._refresh_presets(effect)
        self._rebuild_parameter_rows(effect)
        target_layer = select_target_layer(effect)
        self.status_label.setText(
            f"Aktueller Effekt: {effect['source_id']}::{effect['id']} | Ziel-Layer: {target_layer}"
        )

    def _refresh_presets(self, effect: dict[str, Any]) -> None:
        key = effect["qualified_id"]
        if key not in self.effect_presets:
            self.effect_presets[key] = list(self.backend.list_effect_presets(effect["source_id"], effect["id"]))
        presets = self.effect_presets[key]

        clear_layout(self.preset_layout)
        if not presets:
            self._render_empty_presets()
            return

        for index, preset in enumerate(presets):
            button = QPushButton(self._preset_button_label(preset))
            button.setObjectName(f"preset-button-{preset['preset_id']}")
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            button.setToolTip(preset.get("description") or preset.get("title") or preset["preset_id"])
            color_value = normalize_color_value(preset.get("params", {}).get("color"))
            button.setStyleSheet(color_button_stylesheet(color_value))
            button.clicked.connect(lambda _checked=False, current=preset: self._apply_preset(current))
            row, column = divmod(index, 3)
            self.preset_layout.addWidget(button, row, column)

    def _preset_button_label(self, preset: dict[str, Any]) -> str:
        title = str(preset.get("title") or "").strip()
        if not title:
            return preset["preset_id"]
        return f"{preset['preset_id']} / {title}"

    def _render_empty_presets(self) -> None:
        clear_layout(self.preset_layout)
        placeholder = QLabel("Keine Presets fuer diesen Effekt vorhanden.")
        placeholder.setObjectName("preset-placeholder")
        self.preset_layout.addWidget(placeholder, 0, 0, 1, 3)

    def _render_empty_parameters(self) -> None:
        clear_layout(self.parameter_layout)
        placeholder = QLabel("Keine Parameter verfuegbar.")
        placeholder.setObjectName("parameter-placeholder")
        self.parameter_layout.addWidget(placeholder, 0, 0, 1, 3)

    def _rebuild_parameter_rows(self, effect: dict[str, Any]) -> None:
        clear_layout(self.parameter_layout)
        self.parameter_bindings.clear()

        parameters = effect.get("parameters", {})
        if not isinstance(parameters, dict) or not parameters:
            self._render_empty_parameters()
            return

        row = 0
        for name, meta in parameters.items():
            label = QLabel(name)
            label.setObjectName(f"label-{name}")
            description = str(meta.get("description") or "").strip()
            if description:
                label.setToolTip(description)
            binding = self._create_binding(effect, name, meta)
            self.parameter_bindings[name] = binding
            self.parameter_layout.addWidget(label, row, 0)
            self.parameter_layout.addWidget(binding.primary_widget, row, 1)
            self.parameter_layout.addWidget(binding.secondary_widget, row, 2)
            row += 1

        self.parameter_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding),
            row,
            0,
            1,
            3,
        )
        row += 1

        self.apply_button = QPushButton(build_apply_label(effect))
        self.apply_button.setObjectName("apply-button")
        self.apply_button.clicked.connect(self._apply_current_effect)
        self.parameter_layout.addWidget(self.apply_button, row, 0, 1, 3)

    def _create_binding(self, effect: dict[str, Any], name: str, meta: dict[str, Any]) -> ParameterBinding:
        kind = str(meta.get("type", "")).strip().lower()
        if kind == "color":
            return self._create_color_binding(name, meta)
        if kind in {"int", "float", "duration_ms"}:
            return self._create_numeric_binding(effect, name, meta)
        if kind == "bool":
            return self._create_bool_binding(name, meta)
        if kind == "enum":
            return self._create_enum_binding(name, meta)
        if kind == "color_list":
            return self._create_color_list_binding(name, meta)
        return self._create_text_binding(name, meta)

    def _create_color_binding(self, name: str, meta: dict[str, Any]) -> ParameterBinding:
        line_edit = QLineEdit()
        button = QPushButton("...")
        line_edit.setObjectName(f"param-{name}-text")
        button.setObjectName(f"param-{name}-picker")
        button.setMaximumWidth(52)

        state = {"dirty": False, "updating": False}
        default = normalize_color_value(meta.get("default")) or ""

        def apply_text(raw_value: Any, mark_dirty: bool) -> None:
            text = "" if raw_value is None or raw_value is UNSET else str(raw_value)
            normalized = normalize_color_value(text)
            final_text = normalized or text.strip()
            state["updating"] = True
            try:
                with QSignalBlocker(line_edit):
                    line_edit.setText(final_text)
                button.setStyleSheet(color_button_stylesheet(normalized))
            finally:
                state["updating"] = False
            if mark_dirty:
                state["dirty"] = True

        def on_text_changed(value: str) -> None:
            if state["updating"]:
                return
            apply_text(value, mark_dirty=True)

        def choose_color() -> None:
            chosen = QColorDialog.getColor(QColor(line_edit.text() or default or "#33AAFF"), self, f"Farbe fuer {name}")
            if chosen.isValid():
                apply_text(chosen.name(QColor.NameFormat.HexRgb).upper(), mark_dirty=True)

        line_edit.textChanged.connect(on_text_changed)
        button.clicked.connect(choose_color)
        apply_text(default, mark_dirty=False)

        def get_value() -> Any:
            text = line_edit.text().strip()
            if not text:
                return UNSET if meta.get("default") is None and not state["dirty"] else ""
            normalized = normalize_color_value(text)
            return normalized or text

        return ParameterBinding(
            name=name,
            meta=meta,
            primary_widget=line_edit,
            secondary_widget=button,
            get_api_value=get_value,
            set_api_value=apply_text,
        )

    def _create_numeric_binding(self, effect: dict[str, Any], name: str, meta: dict[str, Any]) -> ParameterBinding:
        presentation = infer_numeric_presentation(effect, name, meta)
        default = meta.get("default")
        state = {"dirty": False, "updating": False}

        if presentation.use_slider:
            if presentation.decimals == 0:
                spin: QSpinBox | QDoubleSpinBox = QSpinBox()
                spin.setRange(int(round(presentation.minimum)), int(round(presentation.maximum)))
                spin.setSingleStep(int(round(max(1.0, presentation.step))))
            else:
                spin = QDoubleSpinBox()
                spin.setDecimals(presentation.decimals)
                spin.setRange(presentation.minimum, presentation.maximum)
                spin.setSingleStep(presentation.step)

            slider = QSlider(Qt.Orientation.Horizontal)
            scale = max(1, int(round(1.0 / presentation.step))) if presentation.step < 1 else 1
            slider.setRange(
                int(round(presentation.minimum * scale)),
                int(round(presentation.maximum * scale)),
            )
            slider.setSingleStep(max(1, int(round(presentation.step * scale))))

            spin.setObjectName(f"param-{name}-spin")
            slider.setObjectName(f"param-{name}-slider")

            def set_value(api_value: Any, mark_dirty: bool) -> None:
                display_value = presentation.api_to_ui(api_value)
                display_value = max(presentation.minimum, min(presentation.maximum, display_value))
                slider_value = int(round(display_value * scale))
                state["updating"] = True
                try:
                    with QSignalBlocker(spin):
                        spin.setValue(int(round(display_value)) if presentation.decimals == 0 else display_value)
                    with QSignalBlocker(slider):
                        slider.setValue(slider_value)
                finally:
                    state["updating"] = False
                if mark_dirty:
                    state["dirty"] = True

            def on_spin_changed(value: float) -> None:
                if state["updating"]:
                    return
                state["dirty"] = True
                set_value(presentation.ui_to_api(float(value)), mark_dirty=True)

            def on_slider_changed(raw: int) -> None:
                if state["updating"]:
                    return
                state["dirty"] = True
                display_value = raw / scale
                if presentation.decimals == 0:
                    display_value = int(round(display_value))
                set_value(presentation.ui_to_api(display_value), mark_dirty=True)

            spin.valueChanged.connect(on_spin_changed)
            slider.valueChanged.connect(on_slider_changed)
            initial = default if default is not None else presentation.minimum
            set_value(initial, mark_dirty=False)

            def get_value() -> Any:
                if default is None and not state["dirty"]:
                    return UNSET
                display_value = float(spin.value())
                return presentation.ui_to_api(display_value)

            return ParameterBinding(
                name=name,
                meta=meta,
                primary_widget=spin,
                secondary_widget=slider,
                get_api_value=get_value,
                set_api_value=set_value,
            )

        spinbox = QDoubleSpinBox()
        spinbox.setDecimals(4)
        spinbox.setRange(-999999999.0, 999999999.0)
        spinbox.setSingleStep(0.1)
        line_edit = QLineEdit()
        spinbox.setObjectName(f"param-{name}-spin")
        line_edit.setObjectName(f"param-{name}-text")

        def set_value(api_value: Any, mark_dirty: bool) -> None:
            text = "" if api_value is None or api_value is UNSET else str(api_value)
            state["updating"] = True
            try:
                with QSignalBlocker(line_edit):
                    line_edit.setText(text)
                parsed = _safe_float(api_value, 0.0)
                with QSignalBlocker(spinbox):
                    spinbox.setValue(parsed)
            finally:
                state["updating"] = False
            if mark_dirty:
                state["dirty"] = True

        def on_line_changed(value: str) -> None:
            if state["updating"]:
                return
            stripped = value.strip()
            if not stripped:
                state["dirty"] = True
                set_value("", mark_dirty=True)
                return
            try:
                parsed = float(stripped.replace(",", "."))
            except ValueError:
                return
            state["dirty"] = True
            set_value(parsed, mark_dirty=True)

        def on_spin_changed(value: float) -> None:
            if state["updating"]:
                return
            state["dirty"] = True
            set_value(round(value, 4), mark_dirty=True)

        line_edit.textChanged.connect(on_line_changed)
        spinbox.valueChanged.connect(on_spin_changed)
        if default is None:
            set_value("", mark_dirty=False)
        else:
            set_value(default, mark_dirty=False)

        def get_value() -> Any:
            text = line_edit.text().strip()
            if not text:
                return UNSET
            value = float(text.replace(",", "."))
            if str(meta.get("type", "")).strip().lower() == "int":
                return int(round(value))
            return value

        return ParameterBinding(
            name=name,
            meta=meta,
            primary_widget=spinbox,
            secondary_widget=line_edit,
            get_api_value=get_value,
            set_api_value=set_value,
        )

    def _create_bool_binding(self, name: str, meta: dict[str, Any]) -> ParameterBinding:
        checkbox = QCheckBox()
        button = QPushButton()
        button.setCheckable(True)
        checkbox.setObjectName(f"param-{name}-checkbox")
        button.setObjectName(f"param-{name}-button")

        state = {"dirty": False, "updating": False}
        default = bool(meta.get("default", False))

        def set_value(value: Any, mark_dirty: bool) -> None:
            checked = bool(value)
            state["updating"] = True
            try:
                with QSignalBlocker(checkbox):
                    checkbox.setChecked(checked)
                with QSignalBlocker(button):
                    button.setChecked(checked)
                    button.setText("An" if checked else "Aus")
            finally:
                state["updating"] = False
            if mark_dirty:
                state["dirty"] = True

        def on_checkbox_changed(checked: bool) -> None:
            if state["updating"]:
                return
            set_value(checked, mark_dirty=True)

        def on_button_toggled(checked: bool) -> None:
            if state["updating"]:
                return
            set_value(checked, mark_dirty=True)

        checkbox.toggled.connect(on_checkbox_changed)
        button.toggled.connect(on_button_toggled)
        set_value(default, mark_dirty=False)

        def get_value() -> Any:
            return bool(checkbox.isChecked())

        return ParameterBinding(
            name=name,
            meta=meta,
            primary_widget=checkbox,
            secondary_widget=button,
            get_api_value=get_value,
            set_api_value=set_value,
        )

    def _create_enum_binding(self, name: str, meta: dict[str, Any]) -> ParameterBinding:
        combo = QComboBox()
        line_edit = QLineEdit()
        combo.setObjectName(f"param-{name}-combo")
        line_edit.setObjectName(f"param-{name}-text")

        values = [str(item) for item in meta.get("enum_values", ())]
        combo.addItems(values)
        state = {"dirty": False, "updating": False}
        default = str(meta.get("default") or (values[0] if values else ""))

        def set_value(value: Any, mark_dirty: bool) -> None:
            text = "" if value is None or value is UNSET else str(value)
            state["updating"] = True
            try:
                with QSignalBlocker(line_edit):
                    line_edit.setText(text)
                with QSignalBlocker(combo):
                    if text in values:
                        combo.setCurrentIndex(values.index(text))
                    elif combo.count():
                        combo.setCurrentIndex(0)
            finally:
                state["updating"] = False
            if mark_dirty:
                state["dirty"] = True

        def on_combo_changed(index: int) -> None:
            if state["updating"] or index < 0:
                return
            set_value(combo.itemText(index), mark_dirty=True)

        def on_line_changed(text: str) -> None:
            if state["updating"]:
                return
            set_value(text.strip(), mark_dirty=True)

        combo.currentIndexChanged.connect(on_combo_changed)
        line_edit.textChanged.connect(on_line_changed)
        set_value(default, mark_dirty=False)

        def get_value() -> Any:
            text = line_edit.text().strip()
            return UNSET if not text and meta.get("default") is None and not state["dirty"] else text

        return ParameterBinding(
            name=name,
            meta=meta,
            primary_widget=combo,
            secondary_widget=line_edit,
            get_api_value=get_value,
            set_api_value=set_value,
        )

    def _create_color_list_binding(self, name: str, meta: dict[str, Any]) -> ParameterBinding:
        first = QLineEdit()
        second = QLineEdit()
        first.setObjectName(f"param-{name}-text-1")
        second.setObjectName(f"param-{name}-text-2")
        default = meta.get("default") or []
        state = {"dirty": False, "updating": False}

        def normalize_list(value: Any) -> str:
            if value is None or value is UNSET:
                return ""
            if isinstance(value, (list, tuple)):
                parts = [normalize_color_value(item) or str(item).strip() for item in value]
                return ", ".join(part for part in parts if part)
            raw = str(value)
            normalized_parts = []
            for part in raw.split(","):
                stripped = part.strip()
                if not stripped:
                    continue
                normalized_parts.append(normalize_color_value(stripped) or stripped)
            return ", ".join(normalized_parts)

        def set_value(value: Any, mark_dirty: bool) -> None:
            text = normalize_list(value)
            state["updating"] = True
            try:
                with QSignalBlocker(first):
                    first.setText(text)
                with QSignalBlocker(second):
                    second.setText(text)
            finally:
                state["updating"] = False
            if mark_dirty:
                state["dirty"] = True

        def on_first_changed(text: str) -> None:
            if state["updating"]:
                return
            set_value(text, mark_dirty=True)

        def on_second_changed(text: str) -> None:
            if state["updating"]:
                return
            set_value(text, mark_dirty=True)

        first.textChanged.connect(on_first_changed)
        second.textChanged.connect(on_second_changed)
        set_value(default, mark_dirty=False)

        def get_value() -> Any:
            text = first.text().strip()
            if not text:
                return UNSET if meta.get("default") is None and not state["dirty"] else []
            return [part.strip() for part in text.split(",") if part.strip()]

        return ParameterBinding(
            name=name,
            meta=meta,
            primary_widget=first,
            secondary_widget=second,
            get_api_value=get_value,
            set_api_value=set_value,
        )

    def _create_text_binding(self, name: str, meta: dict[str, Any]) -> ParameterBinding:
        first = QLineEdit()
        second = QLineEdit()
        first.setObjectName(f"param-{name}-text-1")
        second.setObjectName(f"param-{name}-text-2")
        state = {"dirty": False, "updating": False}
        default = meta.get("default")

        def set_value(value: Any, mark_dirty: bool) -> None:
            text = "" if value is None or value is UNSET else str(value)
            state["updating"] = True
            try:
                with QSignalBlocker(first):
                    first.setText(text)
                with QSignalBlocker(second):
                    second.setText(text)
            finally:
                state["updating"] = False
            if mark_dirty:
                state["dirty"] = True

        def on_changed(text: str) -> None:
            if state["updating"]:
                return
            set_value(text, mark_dirty=True)

        first.textChanged.connect(on_changed)
        second.textChanged.connect(on_changed)
        set_value(default, mark_dirty=False)

        def get_value() -> Any:
            text = first.text().strip()
            if not text:
                return UNSET if default is None and not state["dirty"] else ""
            return text

        return ParameterBinding(
            name=name,
            meta=meta,
            primary_widget=first,
            secondary_widget=second,
            get_api_value=get_value,
            set_api_value=set_value,
        )

    def _collect_effect_params(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for name, binding in self.parameter_bindings.items():
            value = binding.get_api_value()
            if value is UNSET:
                continue
            payload[name] = value
        return payload

    def _apply_current_effect(self) -> None:
        effect = self.current_effect
        if effect is None:
            return
        target_layer = select_target_layer(effect)
        params = self._collect_effect_params()
        try:
            self.backend.apply_effect(effect["source_id"], effect["id"], target_layer, params)
            self.status_label.setText(
                f"Effekt {effect['source_id']}::{effect['id']} auf {target_layer} mit {len(params)} Parametern ausgefuehrt."
            )
        except Exception as exc:
            self.status_label.setText(f"Effekt konnte nicht ausgefuehrt werden: {exc}")
            QMessageBox.critical(self, "Effekt fehlgeschlagen", str(exc))

    def _apply_preset(self, preset: dict[str, Any]) -> None:
        try:
            self.backend.apply_effect_preset(preset["source_id"], preset["preset_id"])
            self.status_label.setText(f"Preset {preset['source_id']}::{preset['preset_id']} angewendet.")
        except Exception as exc:
            self.status_label.setText(f"Preset konnte nicht angewendet werden: {exc}")
            QMessageBox.critical(self, "Preset fehlgeschlagen", str(exc))


def build_arg_parser(script_path: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PySide6-Test-App fuer die Release-EXE des LED Controller Service.")
    parser.add_argument(
        "--service-exe",
        default=str(resolve_default_executable(script_path)),
        help="Pfad zur led_controller_service.exe",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--port-pool", default="")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--use-device",
        dest="use_device",
        action="store_true",
        help="Service mit echter Hardware starten (Standard).",
    )
    mode_group.add_argument(
        "--no-device",
        dest="use_device",
        action="store_false",
        help="Service ohne echte Hardware starten.",
    )
    parser.set_defaults(use_device=True)
    parser.add_argument("--startup-timeout", type=float, default=15.0)
    parser.add_argument("--request-timeout", type=float, default=2.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    script_path = Path(__file__).resolve()
    parser = build_arg_parser(script_path)
    args = parser.parse_args(argv)

    app = QApplication.instance() or QApplication(sys.argv[:1] if argv is None else [sys.argv[0], *argv])
    backend = ReleaseControllerBackend(
        args.service_exe,
        host=args.host,
        requested_port=args.port,
        port_pool=args.port_pool or None,
        startup_timeout=args.startup_timeout,
        request_timeout=args.request_timeout,
        use_device=args.use_device,
        working_directory=Path(args.service_exe).resolve().parent,
    )
    window = EffectTesterWindow(backend)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())


SCRIPT_PATH = Path("P:\\CodexApp\\led_controller_respeaker\\dist\\led_controller_service.exe")

