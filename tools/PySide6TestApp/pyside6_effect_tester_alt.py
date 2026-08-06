from __future__ import annotations

import argparse
import ctypes
import importlib.util
import json
import re
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib import error, request

from PySide6.QtCore import QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from respeaker_led.core.value_normalization import format_color as format_schema_color
except ImportError:
    format_schema_color = None


UNSET = object()
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_PORT_POOL = tuple(range(8765, 8771))
DEFAULT_EFFECT_SET_ROOT = PROJECT_ROOT / "tools" / "effect_building" / "sets"


class _WindowsProcessJob:
    """Owns a Windows job that terminates its complete process tree on close."""

    _KILL_ON_JOB_CLOSE = 0x00002000
    _EXTENDED_LIMIT_INFORMATION = 9

    def __init__(self) -> None:
        self._handle: int | None = None
        if sys.platform != "win32":
            return

        from ctypes import wintypes

        class BasicLimitInformation(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IoCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64),
            ]

        class ExtendedLimitInformation(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimitInformation),
                ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())

        limits = ExtendedLimitInformation()
        limits.BasicLimitInformation.LimitFlags = self._KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            handle,
            self._EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        ):
            error_code = ctypes.get_last_error()
            kernel32.CloseHandle(handle)
            raise ctypes.WinError(error_code)

        self._kernel32 = kernel32
        self._handle = int(handle)

    def assign(self, process: subprocess.Popen[str]) -> None:
        if self._handle is None:
            return
        if not self._kernel32.AssignProcessToJobObject(self._handle, int(process._handle)):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        if self._handle is None:
            return
        self._kernel32.CloseHandle(self._handle)
        self._handle = None


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
    if format_schema_color is not None:
        try:
            return format_schema_color(value)
        except (TypeError, ValueError):
            pass
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


def load_project_version(project_root: Path) -> str | None:
    version_path = project_root / "build-tools" / "version.py"
    if not version_path.is_file():
        return None

    spec = importlib.util.spec_from_file_location("build_tools_version", version_path)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    version = getattr(module, "__version__", None)
    if not isinstance(version, str) or not version.strip():
        return None
    return version.strip().lstrip("v")


def resolve_default_executable(script_path: Path) -> Path:
    project_root = script_path.resolve().parents[2]
    dist_root = project_root / "dist"
    version = load_project_version(project_root)
    versioned_name = f"led_controller_service_{version}.exe" if version else "led_controller_service.exe"

    candidates: list[Path] = [
        dist_root / versioned_name,
        dist_root / "led_controller_service.exe",
        *sorted(dist_root.glob("led_controller_service_*.exe"), reverse=True),
        script_path.with_name(versioned_name),
        script_path.with_name("led_controller_service.exe"),
        script_path.parent / "led_controller_service.exe",
    ]
    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            return candidate
    return candidates[0]


def is_event_like(effect: dict[str, Any]) -> bool:
    tags = set(effect.get("tags", ()))
    layers = set(effect.get("supported_layers", ()))
    return "event" in tags or layers == {"EVENT_LAYER"}


def select_target_layer(effect: dict[str, Any]) -> str:
    definition_type = effect.get("type")
    if definition_type == "event":
        return "EVENT_LAYER"
    if definition_type == "overlay":
        return (
            "TEMP_OVERLAY_LAYER"
            if effect.get("overlay_mode") == "timed"
            else "ONGOING_OVERLAY_LAYER"
        )
    return "STATE_LAYER"


def build_apply_label(effect: dict[str, Any]) -> str:
    tags = set(effect.get("tags", ()))
    if is_event_like(effect):
        return "Effekt einmalig abspielen"
    if "state" in tags:
        return "State setzen"
    return "Effekt setzen"


def format_effect_label(effect: dict[str, Any]) -> str:
    effect_id = effect.get("id", "?")
    title = effect.get("title") or effect_id
    return f"{title}\n{effect_id}"


def effect_type_label(effect: dict[str, Any]) -> str:
    return {
        "state": "State",
        "overlay": "Overlay",
        "event": "Event",
    }.get(str(effect.get("type", "")).lower(), "Effekt")


def load_effect_collections(root: str | Path = DEFAULT_EFFECT_SET_ROOT) -> list[dict[str, Any]]:
    collections: list[dict[str, Any]] = []
    for path in sorted(Path(root).glob("*/set.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("format") != "effect-curation/1":
            continue
        collection_id = str(payload.get("collection_id", "")).strip()
        title = str(payload.get("title", "")).strip()
        source_id = str(payload.get("source_id", "")).strip()
        raw_effects = payload.get("effects", [])
        if not collection_id or not title or not isinstance(raw_effects, list):
            continue
        effect_ids = [
            str(item.get("id", "")).strip()
            for item in raw_effects
            if isinstance(item, dict) and str(item.get("id", "")).strip()
        ]
        collections.append(
            {
                "collection_id": collection_id,
                "title": title,
                "source_id": source_id,
                "effect_ids": effect_ids,
                "path": str(path.resolve()),
            }
        )
    return collections


def _draft_identifier(value: str, fallback: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().casefold()).strip("_")
    return normalized or fallback


def build_preset_draft(
    effect: dict[str, Any],
    params: dict[str, Any],
    *,
    title: str,
    comment: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    effect_id = str(effect.get("id") or "effect")
    normalized_title = title.strip() or f"{effect.get('title') or effect_id} Entwurf"
    return {
        "format": "effect-preset-draft/1",
        "created_at": created_at or datetime.now().astimezone().isoformat(timespec="seconds"),
        "effect": {
            "id": effect_id,
            "qualified_id": effect.get("qualified_id"),
            "title": effect.get("title"),
            "type": effect.get("type"),
            "source_id": effect.get("source_id"),
            "package_id": effect.get("package_id"),
        },
        "preset_draft": {
            "suggested_id": _draft_identifier(normalized_title, f"{effect_id}_draft"),
            "title": normalized_title,
            "comment": comment.strip(),
            "params": dict(params),
        },
    }


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
            maximum=3000.0,
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
            derived_max = 15000.0
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
        self._process_job: _WindowsProcessJob | None = None

    @property
    def runtime_state_file(self) -> Path:
        return self.working_directory / "runtime_state" / "active_service.json"

    def start(self) -> dict[str, Any]:
        if not self.executable_path.exists():
            raise FileNotFoundError(f"Service executable not found: {self.executable_path}")
        if self.process is not None and self.process.poll() is None:
            raise RuntimeError("Controller service is already running")
        if self.use_device:
            existing = self._find_existing_device_controller()
            if existing is not None:
                raise RuntimeError(
                    "Ein LED-Controller mit Hardwarezugriff laeuft bereits auf "
                    f"{existing['host']}:{existing['port']}. Schliesse zuerst das andere "
                    "Effect-Studio, damit nicht zwei Prozesse gleichzeitig auf den ReSpeaker zugreifen."
                )

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
        process_job = _WindowsProcessJob()
        try:
            self.process = subprocess.Popen(
                command,
                cwd=str(self.working_directory),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
            process_job.assign(self.process)
        except Exception:
            process_job.close()
            if self.process is not None and self.process.poll() is None:
                self.process.terminate()
            self.process = None
            raise
        self._process_job = process_job
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

    def _find_existing_device_controller(self) -> dict[str, Any] | None:
        ports = {self.requested_port, *DEFAULT_PORT_POOL}
        if self.port_pool:
            for raw in self.port_pool.split(","):
                try:
                    ports.add(int(raw.strip()))
                except ValueError:
                    continue
        for port in sorted(value for value in ports if value > 0):
            try:
                status = ControllerHttpClient(
                    self.host,
                    port,
                    timeout=min(0.25, self.request_timeout),
                ).request_json("GET", "/api/v1/status")
            except RuntimeError:
                continue
            if (
                status.get("render_loop_running")
                and status.get("requested_output_mode") == "device"
            ):
                return {"host": self.host, "port": port}
        return None

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
            if self._process_job is not None:
                self._process_job.close()
                self._process_job = None

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
        self._effect_details: dict[tuple[str, str], dict[str, Any]] = {}

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
        self._effect_details.clear()
        effects: list[dict[str, Any]] = []
        for path in ("states", "overlays", "events"):
            payload = self._client().request_json("GET", f"/api/v2/{path}?details=true")
            for raw in payload:
                item = dict(raw)
                item["supported_layers"] = [select_target_layer(item)]
                runtime_inputs = dict(item.get("runtime_inputs", {}))
                item["parameters"] = {**dict(item.get("parameters", {})), **runtime_inputs}
                item["_runtime_input_names"] = list(runtime_inputs)
                self._effect_details[(item["source_id"], item["id"])] = item
                effects.append(item)
        return effects

    def reload_effects(self) -> list[dict[str, Any]]:
        self._client().request_json("POST", "/api/v1/effect-sources/reload")
        return self.list_effects()

    def list_effect_presets(self, source_id: str, effect_id: str) -> list[dict[str, Any]]:
        payload = self._client().request_json("GET", "/api/v2/presets?details=true")
        return [
            item
            for item in payload
            if item.get("source_id") == source_id and item.get("effect_id") == effect_id
        ]

    def apply_effect(self, source_id: str, effect_id: str, target_layer: str, params: dict[str, Any]) -> dict[str, Any]:
        target = f"{source_id}::{effect_id}"
        detail = self._effect_details.get((source_id, effect_id), {})
        input_names = set(detail.get("_runtime_input_names", ()))
        config = {name: value for name, value in params.items() if name not in input_names}
        inputs = {name: value for name, value in params.items() if name in input_names}
        if target_layer == "EVENT_LAYER":
            return self._client().request_json(
                "POST",
                "/api/v2/emit/event",
                {"target": target, "config": config},
            )
        if target_layer in {"TEMP_OVERLAY_LAYER", "ONGOING_OVERLAY_LAYER"}:
            return self._client().request_json(
                "POST",
                "/api/v2/set/overlay",
                {
                    "target": target,
                    "channel": "effect_tester",
                    "config": config,
                    "inputs": inputs,
                },
            )
        return self._client().request_json(
            "POST",
            "/api/v2/set/state",
            {"target": target, "config": config},
        )

    def apply_effect_preset(self, source_id: str, preset_id: str) -> dict[str, Any]:
        from urllib.parse import quote

        target = f"{source_id}::{preset_id}"
        detail = self._client().request_json("GET", f"/api/v2/show/{quote(target, safe='')}")
        if detail.get("type") == "event":
            path = "/api/v2/emit/event"
            payload = {"target": target}
        elif detail.get("type") == "overlay":
            path = "/api/v2/set/overlay"
            payload = {"target": target, "channel": "effect_tester"}
        else:
            path = "/api/v2/set/state"
            payload = {"target": target}
        return self._client().request_json("POST", path, payload)

    def clear_effect(self, definition_type: str) -> dict[str, Any]:
        if definition_type == "state":
            return self._client().request_json(
                "POST",
                "/api/v2/clear/state",
                {"slot": "primary"},
            )
        if definition_type == "overlay":
            return self._client().request_json(
                "POST",
                "/api/v2/clear/overlay",
                {"channel": "effect_tester"},
            )
        return {"ok": True, "message": "Events end automatically"}

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
    def __init__(self, backend: Any, *, effect_collections: list[dict[str, Any]] | None = None) -> None:
        super().__init__()
        self.backend = backend
        self.effect_collections = list(load_effect_collections() if effect_collections is None else effect_collections)
        self.effects: list[dict[str, Any]] = []
        self.filtered_effects: list[dict[str, Any]] = []
        self.effect_presets: dict[str, list[dict[str, Any]]] = {}
        self.parameter_bindings: dict[str, ParameterBinding] = {}
        self.current_effect: dict[str, Any] | None = None
        self._suppress_live_updates = False

        self.setWindowTitle("LED Effect Studio")
        self.setFont(QFont("Segoe UI", 10))
        self.resize(1180, 820)
        self.setMinimumSize(920, 640)

        self.status_label = QLabel("Starte Service ...")
        self.status_label.setObjectName("status-label")
        self.status_label.setWordWrap(True)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("effect-search")
        self.search_edit.setPlaceholderText("Effekte durchsuchen")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._apply_effect_filters)

        self.type_filter = QComboBox()
        self.type_filter.setObjectName("type-filter")
        self.type_filter.addItem("Alle Typen", "")
        self.type_filter.addItem("States", "state")
        self.type_filter.addItem("Overlays", "overlay")
        self.type_filter.addItem("Events", "event")
        self.type_filter.currentIndexChanged.connect(self._apply_effect_filters)

        self.package_filter = QComboBox()
        self.package_filter.setObjectName("package-filter")
        self.package_filter.addItem("Alle Pakete und Sets", "")
        self.package_filter.currentIndexChanged.connect(self._apply_effect_filters)

        self.effect_list = QListWidget()
        self.effect_list.setObjectName("effect-list")
        self.effect_list.setAlternatingRowColors(True)
        self.effect_list.setWordWrap(True)
        self.effect_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.effect_list.currentRowChanged.connect(self._on_effect_changed)

        self.effect_count_label = QLabel("0 Effekte")
        self.effect_count_label.setObjectName("effect-count")

        self.reload_button = QPushButton("Neu laden")
        self.reload_button.setObjectName("reload-button")
        self.reload_button.clicked.connect(self._reload_effects)

        library_panel = QWidget()
        library_panel.setObjectName("library-panel")
        library_layout = QVBoxLayout(library_panel)
        library_layout.setContentsMargins(16, 16, 16, 16)
        library_layout.setSpacing(10)
        library_title = QLabel("Effektbibliothek")
        library_title.setObjectName("panel-title")
        library_layout.addWidget(library_title)
        library_layout.addWidget(self.search_edit)
        library_layout.addWidget(self.type_filter)
        library_layout.addWidget(self.package_filter)
        library_layout.addWidget(self.effect_list, 1)
        library_footer = QHBoxLayout()
        library_footer.addWidget(self.effect_count_label)
        library_footer.addStretch(1)
        library_footer.addWidget(self.reload_button)
        library_layout.addLayout(library_footer)

        self.effect_title_label = QLabel("Kein Effekt ausgewaehlt")
        self.effect_title_label.setObjectName("effect-title")
        self.effect_title_label.setWordWrap(True)
        self.effect_meta_label = QLabel("")
        self.effect_meta_label.setObjectName("effect-meta")
        self.effect_meta_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.effect_description_label = QLabel("")
        self.effect_description_label.setObjectName("effect-description")
        self.effect_description_label.setWordWrap(True)

        self.preset_group = QGroupBox("Presets")
        self.preset_layout = QGridLayout()
        self.preset_group.setLayout(self.preset_layout)

        self.parameter_group = QGroupBox("Parameter")
        self.parameter_layout = QGridLayout()
        self.parameter_layout.setColumnStretch(1, 1)
        self.parameter_layout.setColumnStretch(2, 2)
        self.parameter_group.setLayout(self.parameter_layout)

        self.draft_group = QGroupBox("Parameterentwurf festhalten")
        draft_layout = QGridLayout()
        self.draft_title_edit = QLineEdit()
        self.draft_title_edit.setObjectName("draft-title")
        self.draft_title_edit.setPlaceholderText("Bezeichnung des Entwurfs")
        self.draft_comment_edit = QPlainTextEdit()
        self.draft_comment_edit.setObjectName("draft-comment")
        self.draft_comment_edit.setPlaceholderText("Gedachter Einsatz, Eindruck oder offene Feinabstimmung")
        self.draft_comment_edit.setMaximumHeight(82)
        self.copy_draft_button = QPushButton("JSON kopieren")
        self.copy_draft_button.setObjectName("copy-draft-button")
        self.copy_draft_button.clicked.connect(self._copy_preset_draft)
        self.export_draft_button = QPushButton("JSON exportieren ...")
        self.export_draft_button.setObjectName("export-draft-button")
        self.export_draft_button.clicked.connect(self._export_preset_draft)
        draft_layout.addWidget(QLabel("Bezeichnung"), 0, 0)
        draft_layout.addWidget(self.draft_title_edit, 0, 1, 1, 2)
        draft_layout.addWidget(QLabel("Kommentar"), 1, 0, Qt.AlignmentFlag.AlignTop)
        draft_layout.addWidget(self.draft_comment_edit, 1, 1, 1, 2)
        draft_layout.addWidget(self.copy_draft_button, 2, 1)
        draft_layout.addWidget(self.export_draft_button, 2, 2)
        draft_layout.setColumnStretch(1, 1)
        draft_layout.setColumnStretch(2, 1)
        self.draft_group.setLayout(draft_layout)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 8, 8)
        scroll_layout.setSpacing(14)
        scroll_layout.addWidget(self.preset_group)
        scroll_layout.addWidget(self.parameter_group)
        scroll_layout.addWidget(self.draft_group)
        scroll_layout.addStretch(1)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("effect-scroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setWidget(scroll_content)

        self.live_preview_checkbox = QCheckBox("Live aktualisieren")
        self.live_preview_checkbox.setObjectName("live-preview")
        self.live_preview_checkbox.setChecked(False)

        self.reset_values_button = QPushButton("Defaults")
        self.reset_values_button.setObjectName("reset-values-button")
        self.reset_values_button.clicked.connect(self._reset_parameter_values)

        self.clear_button = QPushButton("Aktiven Layer leeren")
        self.clear_button.setObjectName("clear-effect-button")
        self.clear_button.clicked.connect(self._clear_current_effect)

        self.apply_button = QPushButton("Anwenden")
        self.apply_button.setObjectName("apply-button")
        self.apply_button.clicked.connect(lambda _checked=False: self._apply_current_effect())

        self.live_apply_timer = QTimer(self)
        self.live_apply_timer.setSingleShot(True)
        self.live_apply_timer.setInterval(180)
        self.live_apply_timer.timeout.connect(self._apply_live_preview)

        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 8, 0, 0)
        action_layout.addWidget(self.live_preview_checkbox)
        action_layout.addStretch(1)
        action_layout.addWidget(self.reset_values_button)
        action_layout.addWidget(self.clear_button)
        action_layout.addWidget(self.apply_button)

        detail_panel = QWidget()
        detail_panel.setObjectName("detail-panel")
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(22, 18, 22, 18)
        detail_layout.setSpacing(8)
        detail_layout.addWidget(self.effect_title_label)
        detail_layout.addWidget(self.effect_meta_label)
        detail_layout.addWidget(self.effect_description_label)
        detail_layout.addSpacing(4)
        detail_layout.addWidget(scroll_area, 1)
        detail_layout.addLayout(action_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("main-splitter")
        splitter.addWidget(library_panel)
        splitter.addWidget(detail_panel)
        splitter.setSizes([310, 870])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        container = QWidget()
        root_layout = QVBoxLayout(container)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self.status_label)
        root_layout.addWidget(splitter, 1)
        self.setCentralWidget(container)

        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #F4F5F7;
                color: #20242A;
                font-size: 10pt;
            }
            #status-label {
                background: #E8F5EE;
                border-bottom: 1px solid #B9D7C5;
                color: #185B37;
                padding: 8px 14px;
            }
            #library-panel {
                background: #ECEFF2;
                border-right: 1px solid #CCD1D7;
            }
            #detail-panel, #effect-scroll, #effect-scroll > QWidget > QWidget {
                background: #FFFFFF;
            }
            #panel-title {
                font-size: 15pt;
                font-weight: 600;
            }
            #effect-title {
                font-size: 18pt;
                font-weight: 600;
                color: #171A1F;
            }
            #effect-meta, #effect-count {
                color: #606873;
                font-size: 9pt;
            }
            #effect-description {
                color: #3E4650;
                padding-bottom: 5px;
            }
            QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QListWidget {
                background: #FFFFFF;
                border: 1px solid #BFC5CC;
                border-radius: 4px;
                padding: 6px;
                selection-background-color: #245EAA;
            }
            QListWidget::item {
                min-height: 44px;
                padding: 5px 7px;
                border-bottom: 1px solid #E1E4E8;
            }
            QListWidget::item:selected {
                background: #DDEAFF;
                color: #173E73;
            }
            QGroupBox {
                background: #FFFFFF;
                border: 1px solid #D4D8DD;
                border-radius: 5px;
                margin-top: 11px;
                padding: 12px 10px 8px 10px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QPushButton {
                background: #EEF0F3;
                border: 1px solid #B9C0C8;
                border-radius: 4px;
                padding: 7px 12px;
            }
            QPushButton:hover {
                background: #E2E6EA;
            }
            #apply-button {
                background: #245EAA;
                border-color: #1E518F;
                color: #FFFFFF;
                font-weight: 600;
                min-width: 125px;
            }
            #apply-button:hover {
                background: #1E518F;
            }
            #clear-effect-button {
                color: #8B2E25;
            }
            QSlider::groove:horizontal {
                height: 5px;
                background: #D7DBE0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
                background: #245EAA;
            }
            """
        )

        self._start_backend_and_load_effects()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        try:
            self.backend.close()
        finally:
            super().closeEvent(event)

    def _start_backend_and_load_effects(self) -> None:
        try:
            binding = self.backend.start()
            status: dict[str, Any] = {}
            get_status = getattr(self.backend, "get_status", None)
            if callable(get_status):
                backend_status = get_status()
                if isinstance(backend_status, dict):
                    status = backend_status
            output_mode = status.get("output_mode") or "unbekannt"
            fps = status.get("fps")
            fps_text = f" | {fps:g} FPS" if isinstance(fps, (int, float)) else ""
            self.status_label.setText(
                f"Verbunden mit {binding['host']}:{binding['port']} | Ausgabe: {output_mode}{fps_text}"
            )
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
                key=lambda item: (
                    {"state": 0, "overlay": 1, "event": 2}.get(item.get("type"), 3),
                    item.get("title", ""),
                    item.get("id", ""),
                ),
            )
            self._refresh_package_filter()
            self._apply_effect_filters()
        except Exception as exc:
            self.effect_list.setEnabled(False)
            self.status_label.setText(f"Service konnte nicht gestartet werden: {exc}")
            QMessageBox.critical(self, "Service-Start fehlgeschlagen", str(exc))

    def _reload_effects(self) -> None:
        current_id = self.current_effect.get("qualified_id") if self.current_effect else None
        try:
            reload_effects = getattr(self.backend, "reload_effects", None)
            self.effects = list(reload_effects() if callable(reload_effects) else self.backend.list_effects())
            self.effect_presets.clear()
            self.effects.sort(
                key=lambda item: (
                    {"state": 0, "overlay": 1, "event": 2}.get(item.get("type"), 3),
                    item.get("title", ""),
                    item.get("id", ""),
                )
            )
            self._refresh_package_filter()
            self._apply_effect_filters(preferred_id=current_id)
            self.status_label.setText(f"Effektbibliothek neu geladen: {len(self.effects)} Effekte.")
        except Exception as exc:
            self.status_label.setText(f"Effektbibliothek konnte nicht geladen werden: {exc}")
            QMessageBox.critical(self, "Neuladen fehlgeschlagen", str(exc))

    def _apply_effect_filters(self, *_args: Any, preferred_id: str | None = None) -> None:
        selected_id = preferred_id
        if selected_id is None and self.current_effect is not None:
            selected_id = self.current_effect.get("qualified_id")
        query = self.search_edit.text().strip().casefold()
        definition_type = str(self.type_filter.currentData() or "")
        package_filter = str(self.package_filter.currentData() or "")
        self.filtered_effects = []
        for effect in self.effects:
            if definition_type and effect.get("type") != definition_type:
                continue
            if package_filter and not self._matches_package_filter(effect, package_filter):
                continue
            haystack = " ".join(
                str(effect.get(name) or "")
                for name in ("id", "qualified_id", "title", "description", "source_id", "tags")
            ).casefold()
            if query and query not in haystack:
                continue
            self.filtered_effects.append(effect)

        with QSignalBlocker(self.effect_list):
            self.effect_list.clear()
            preferred_row = -1
            for row, effect in enumerate(self.filtered_effects):
                item = QListWidgetItem(format_effect_label(effect))
                item.setData(Qt.ItemDataRole.UserRole, effect.get("qualified_id"))
                item.setToolTip(effect.get("description") or effect.get("qualified_id") or "")
                self.effect_list.addItem(item)
                if effect.get("qualified_id") == selected_id:
                    preferred_row = row

        self.effect_count_label.setText(f"{len(self.filtered_effects)} von {len(self.effects)}")
        if self.filtered_effects:
            row = preferred_row if preferred_row >= 0 else 0
            with QSignalBlocker(self.effect_list):
                self.effect_list.setCurrentRow(row)
            self._on_effect_changed(row)
        else:
            self.current_effect = None
            self._render_empty_presets()
            self._render_empty_parameters()
            self._update_effect_header(None)

    def _refresh_package_filter(self) -> None:
        selected = str(self.package_filter.currentData() or "")
        options: list[tuple[str, str]] = [("Alle Pakete und Sets", "")]
        source_ids = sorted({str(effect.get("source_id") or "") for effect in self.effects if effect.get("source_id")})
        options.extend((f"Paket: {source_id}", f"source:{source_id}") for source_id in source_ids)
        options.extend(
            (f"Set: {collection['title']}", f"collection:{collection['collection_id']}")
            for collection in self.effect_collections
        )
        with QSignalBlocker(self.package_filter):
            self.package_filter.clear()
            for label, value in options:
                self.package_filter.addItem(label, value)
            selected_index = self.package_filter.findData(selected)
            self.package_filter.setCurrentIndex(max(0, selected_index))

    def _matches_package_filter(self, effect: dict[str, Any], package_filter: str) -> bool:
        kind, _, identifier = package_filter.partition(":")
        if kind == "source":
            return effect.get("source_id") == identifier
        if kind != "collection":
            return True
        for collection in self.effect_collections:
            if collection.get("collection_id") != identifier:
                continue
            source_id = str(collection.get("source_id") or "")
            return (
                (not source_id or effect.get("source_id") == source_id)
                and effect.get("id") in set(collection.get("effect_ids", ()))
            )
        return False

    def _on_effect_changed(self, index: int) -> None:
        if index < 0 or index >= len(self.filtered_effects):
            self.current_effect = None
            self._render_empty_presets()
            self._render_empty_parameters()
            self._update_effect_header(None)
            return
        effect = self.filtered_effects[index]

        self.live_apply_timer.stop()
        self.current_effect = effect
        previous_effect_id = self.draft_group.property("effect-id")
        if previous_effect_id != effect.get("qualified_id"):
            self.draft_group.setProperty("effect-id", effect.get("qualified_id"))
            self.draft_title_edit.setText(f"{effect.get('title') or effect.get('id')} Entwurf")
            self.draft_comment_edit.clear()
        self._update_effect_header(effect)
        self._refresh_presets(effect)
        self._rebuild_parameter_rows(effect)
        target_layer = select_target_layer(effect)
        definition_type = str(effect.get("type") or "")
        self.live_preview_checkbox.setEnabled(definition_type != "event")
        self.clear_button.setEnabled(definition_type != "event")
        if definition_type == "event":
            self.live_preview_checkbox.setChecked(False)
        self.status_label.setText(
            f"Aktueller Effekt: {effect['source_id']}::{effect['id']} | Ziel-Layer: {target_layer}"
        )

    def _update_effect_header(self, effect: dict[str, Any] | None) -> None:
        if effect is None:
            self.effect_title_label.setText("Keine Treffer")
            self.effect_meta_label.setText("")
            self.effect_description_label.setText("")
            self.apply_button.setEnabled(False)
            self.reset_values_button.setEnabled(False)
            self.clear_button.setEnabled(False)
            self.copy_draft_button.setEnabled(False)
            self.export_draft_button.setEnabled(False)
            return

        self.effect_title_label.setText(str(effect.get("title") or effect.get("id") or "Effekt"))
        metadata = [
            effect_type_label(effect),
            str(effect.get("qualified_id") or ""),
        ]
        overlay_mode = effect.get("overlay_mode")
        if overlay_mode:
            metadata.append(str(overlay_mode))
        self.effect_meta_label.setText("  |  ".join(item for item in metadata if item))
        self.effect_description_label.setText(str(effect.get("description") or ""))
        self.apply_button.setEnabled(True)
        self.reset_values_button.setEnabled(True)
        self.copy_draft_button.setEnabled(True)
        self.export_draft_button.setEnabled(True)
        self.apply_button.setText(build_apply_label(effect))

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
            tooltip = f"{preset.get('source_id', '?')}::{preset['preset_id']}"
            if preset.get("description"):
                tooltip = f"{tooltip}\n{preset['description']}"
            button.setToolTip(tooltip)
            color_value = normalize_color_value(preset.get("params", {}).get("color"))
            button.setStyleSheet(color_button_stylesheet(color_value))
            button.clicked.connect(lambda _checked=False, current=preset: self._apply_preset(current))
            row, column = divmod(index, 3)
            self.preset_layout.addWidget(button, row, column)

    def _preset_button_label(self, preset: dict[str, Any]) -> str:
        title = str(preset.get("title") or "").strip()
        return title or preset["preset_id"]

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
            self._connect_live_preview(binding.primary_widget)
            self._connect_live_preview(binding.secondary_widget)
            row += 1

    def _connect_live_preview(self, widget: QWidget) -> None:
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(self._schedule_live_apply)
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.valueChanged.connect(self._schedule_live_apply)
        elif isinstance(widget, QSlider):
            widget.valueChanged.connect(self._schedule_live_apply)
        elif isinstance(widget, QCheckBox):
            widget.toggled.connect(self._schedule_live_apply)
        elif isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(self._schedule_live_apply)
        elif isinstance(widget, QPushButton) and widget.isCheckable():
            widget.toggled.connect(self._schedule_live_apply)

    def _schedule_live_apply(self, *_args: Any) -> None:
        effect = self.current_effect
        if (
            self._suppress_live_updates
            or effect is None
            or effect.get("type") == "event"
            or not self.live_preview_checkbox.isChecked()
        ):
            return
        self.live_apply_timer.start()

    def _reset_parameter_values(self) -> None:
        self.live_apply_timer.stop()
        self._suppress_live_updates = True
        try:
            for binding in self.parameter_bindings.values():
                binding.set_api_value(binding.meta.get("default", UNSET), False)
        finally:
            self._suppress_live_updates = False
        self.status_label.setText("Parameter auf die Effekt-Defaults zurueckgesetzt.")
        self._schedule_live_apply()

    def _apply_values_to_controls(self, values: dict[str, Any]) -> None:
        self._suppress_live_updates = True
        try:
            for binding in self.parameter_bindings.values():
                binding.set_api_value(binding.meta.get("default", UNSET), False)
            for name, value in values.items():
                binding = self.parameter_bindings.get(name)
                if binding is not None:
                    binding.set_api_value(value, True)
        finally:
            self._suppress_live_updates = False

    def _clear_current_effect(self) -> None:
        effect = self.current_effect
        if effect is None or effect.get("type") == "event":
            return
        try:
            clear_effect = getattr(self.backend, "clear_effect")
            clear_effect(str(effect.get("type") or ""))
            self.status_label.setText(f"Aktiver {effect_type_label(effect)}-Layer wurde geleert.")
        except Exception as exc:
            self.status_label.setText(f"Layer konnte nicht geleert werden: {exc}")
            QMessageBox.critical(self, "Leeren fehlgeschlagen", str(exc))

    def _create_binding(self, effect: dict[str, Any], name: str, meta: dict[str, Any]) -> ParameterBinding:
        kind = str(meta.get("type", "")).strip().lower()
        if kind == "color":
            return self._create_color_binding(name, meta)
        if kind in {"int", "float", "duration_ms", "angle_deg"}:
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
        kind = str(meta.get("type") or "").strip().lower()

        def set_value(value: Any, mark_dirty: bool) -> None:
            if value is None or value is UNSET:
                text = ""
            elif kind in {"gradient", "color_range"} and isinstance(value, (list, dict)):
                text = json.dumps(value, ensure_ascii=True, separators=(",", ":"))
            else:
                text = str(value)
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
            if kind in {"gradient", "color_range"}:
                try:
                    return json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{name} enthaelt kein gueltiges JSON: {exc.msg}") from exc
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

    def _build_current_preset_draft(self) -> dict[str, Any]:
        if self.current_effect is None:
            raise ValueError("Kein Effekt fuer den Parameterentwurf ausgewaehlt")
        return build_preset_draft(
            self.current_effect,
            self._collect_effect_params(),
            title=self.draft_title_edit.text(),
            comment=self.draft_comment_edit.toPlainText(),
        )

    def _copy_preset_draft(self) -> None:
        try:
            payload = self._build_current_preset_draft()
            text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
            QApplication.clipboard().setText(text)
            self.status_label.setText(
                f"Parameterentwurf fuer {payload['effect']['id']} in die Zwischenablage kopiert."
            )
        except Exception as exc:
            self.status_label.setText(f"Parameterentwurf konnte nicht kopiert werden: {exc}")
            QMessageBox.critical(self, "Kopieren fehlgeschlagen", str(exc))

    def _export_preset_draft(self) -> None:
        try:
            payload = self._build_current_preset_draft()
            effect_id = str(payload["effect"]["id"])
            default_path = PROJECT_ROOT / f"{effect_id}_preset_draft.json"
            target, _selected_filter = QFileDialog.getSaveFileName(
                self,
                "Parameterentwurf exportieren",
                str(default_path),
                "JSON-Dateien (*.json)",
            )
            if not target:
                return
            target_path = Path(target)
            target_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self.status_label.setText(f"Parameterentwurf exportiert: {target_path}")
        except Exception as exc:
            self.status_label.setText(f"Parameterentwurf konnte nicht exportiert werden: {exc}")
            QMessageBox.critical(self, "Export fehlgeschlagen", str(exc))

    def _apply_live_preview(self) -> None:
        self._apply_current_effect(show_errors=False)

    def _apply_current_effect(self, *, show_errors: bool = True) -> None:
        effect = self.current_effect
        if effect is None:
            return
        target_layer = select_target_layer(effect)
        try:
            params = self._collect_effect_params()
            self.backend.apply_effect(effect["source_id"], effect["id"], target_layer, params)
            self.status_label.setText(
                f"Effekt {effect['source_id']}::{effect['id']} auf {target_layer} mit {len(params)} Parametern ausgefuehrt."
            )
        except Exception as exc:
            self.status_label.setText(f"Effekt konnte nicht ausgefuehrt werden: {exc}")
            if show_errors:
                QMessageBox.critical(self, "Effekt fehlgeschlagen", str(exc))

    def _apply_preset(self, preset: dict[str, Any]) -> None:
        try:
            self._apply_values_to_controls(dict(preset.get("params") or {}))
            self.draft_title_edit.setText(f"{self._preset_button_label(preset)} Entwurf")
            self.backend.apply_effect_preset(preset["source_id"], preset["preset_id"])
            self.status_label.setText(f"Preset {preset['source_id']}::{preset['preset_id']} angewendet.")
        except Exception as exc:
            self.status_label.setText(f"Preset konnte nicht angewendet werden: {exc}")
            QMessageBox.critical(self, "Preset fehlgeschlagen", str(exc))


def build_arg_parser(script_path: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V2-Effektbrowser fuer den aktuellen LED-Controller-Quellstand oder eine Release-EXE."
    )
    parser.add_argument(
        "--service-exe",
        default=None,
        help="Optionaler Pfad zur led_controller_service.exe; ohne Angabe wird main.py aus dem Projekt gestartet.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--port-pool", default="")
    parser.add_argument("--fps", type=float, default=8.0)
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
    project_root = script_path.parents[2]
    if args.service_exe:
        executable_path = Path(args.service_exe).resolve()
        service_arguments = ["--fps", str(args.fps)]
        working_directory = executable_path.parent
    else:
        executable_path = Path(sys.executable).resolve()
        service_arguments = [str(project_root / "main.py"), "--fps", str(args.fps)]
        working_directory = project_root

    backend = ReleaseControllerBackend(
        executable_path,
        host=args.host,
        requested_port=args.port,
        port_pool=args.port_pool or None,
        startup_timeout=args.startup_timeout,
        request_timeout=args.request_timeout,
        use_device=args.use_device,
        service_arguments=service_arguments,
        working_directory=working_directory,
    )
    window = EffectTesterWindow(backend)
    window.show()
    app.aboutToQuit.connect(backend.close)
    try:
        return app.exec()
    finally:
        backend.close()


if __name__ == "__main__":
    raise SystemExit(main())

