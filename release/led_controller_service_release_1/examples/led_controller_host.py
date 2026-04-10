from __future__ import annotations

import json
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable
from urllib import error, request


class LedControllerRelease1:
    def __init__(
        self,
        executable_path: str | Path,
        *,
        host: str = "127.0.0.1",
        requested_port: int = 8765,
        port_pool: str | None = None,
        startup_timeout: float = 15.0,
        request_timeout: float = 2.0,
        on_output: Callable[[str], None] | None = None,
    ) -> None:
        self.executable_path = Path(executable_path).resolve()
        self.host = host
        self.requested_port = int(requested_port)
        self.port_pool = port_pool
        self.startup_timeout = float(startup_timeout)
        self.request_timeout = float(request_timeout)
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
    def base_url(self) -> str:
        if self.bound_host is None or self.bound_port is None:
            raise RuntimeError("Controller service is not bound yet")
        return f"http://{self.bound_host}:{self.bound_port}"

    @property
    def runtime_state_file(self) -> Path:
        return self.executable_path.parent / "runtime_state" / "active_service.json"

    def start(self, *, use_device: bool = True, extra_args: list[str] | None = None) -> dict[str, Any]:
        if self.process is not None and self.process.poll() is None:
            raise RuntimeError("Controller service is already running")

        self._binding_event.clear()
        self.binding = None
        self.bound_host = None
        self.bound_port = None

        command = [str(self.executable_path)]
        if not use_device:
            command.append("--no-device")
        command.extend(["serve", "--host", self.host, "--port", str(self.requested_port)])
        if self.port_pool:
            command.extend(["--port-pool", self.port_pool])
        if extra_args:
            command.extend(extra_args)

        self.process = subprocess.Popen(
            command,
            cwd=str(self.executable_path.parent),
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
            fallback = self._read_active_service_file()
            if fallback is not None:
                self._set_binding(fallback)
                return dict(self.binding or {})

        recent_output = "\n".join(self._recent_output)
        raise RuntimeError(f"Controller service did not bind in time. Recent output:\n{recent_output}")

    def ping(self) -> dict[str, Any]:
        return self._request_json("GET", "/api/v1/ping")

    def status(self) -> dict[str, Any]:
        return self._request_json("GET", "/api/v1/status")

    def list_effects(self) -> dict[str, Any]:
        return self._request_json("GET", "/api/v1/effects")

    def list_presets(self) -> dict[str, Any]:
        return self._request_json("GET", "/api/v1/presets")

    def set_state(self, state_name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request_json("POST", "/api/v1/commands/set_state", {"state_name": state_name, "payload": payload or {}})

    def clear_state(self, state_name: str | None = None) -> dict[str, Any]:
        return self._request_json("POST", "/api/v1/commands/clear_state", {"state_name": state_name})

    def emit_event(self, event_name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request_json("POST", "/api/v1/commands/emit_event", {"event_name": event_name, "payload": payload or {}})

    def apply_effect(
        self,
        effect_id: str,
        target_layer: str,
        params: dict[str, Any] | None = None,
        *,
        duration_ms: int | None = None,
        priority: int | None = None,
        enqueue: bool = False,
        replace_existing: bool = True,
    ) -> dict[str, Any]:
        return self._request_json(
            "POST",
            "/api/v1/commands/apply_effect",
            {
                "effect_id": effect_id,
                "target_layer": target_layer,
                "params": params or {},
                "duration_ms": duration_ms,
                "priority": priority,
                "enqueue": enqueue,
                "replace_existing": replace_existing,
            },
        )

    def clear_layer(self, target_layer: str) -> dict[str, Any]:
        return self._request_json("POST", "/api/v1/commands/clear_layer", {"target_layer": target_layer})

    def reset(self) -> dict[str, Any]:
        return self._request_json("POST", "/api/v1/commands/reset")

    def shutdown(self) -> dict[str, Any]:
        return self._request_json("POST", "/api/v1/commands/shutdown")

    def start_countdown(
        self,
        total_ms: int,
        remaining_ms: int | None = None,
        *,
        follow_up_state: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request_json(
            "POST",
            "/api/v1/commands/start_timeout_countdown",
            {
                "total_ms": total_ms,
                "remaining_ms": remaining_ms,
                "follow_up_state": follow_up_state,
                "payload": payload or {},
            },
        )

    def update_countdown(self, remaining_ms: int) -> dict[str, Any]:
        return self._request_json("POST", "/api/v1/commands/update_timeout_countdown", {"remaining_ms": remaining_ms})

    def cancel_countdown(self) -> dict[str, Any]:
        return self._request_json("POST", "/api/v1/commands/cancel_timeout_countdown")

    def set_direction(self, direction_deg: float) -> dict[str, Any]:
        return self._request_json("POST", "/api/v1/commands/set_direction", {"direction_deg": direction_deg})

    def clear_direction(self) -> dict[str, Any]:
        return self._request_json("POST", "/api/v1/commands/clear_direction")

    def set_brightness(self, level: float) -> dict[str, Any]:
        return self._request_json("POST", "/api/v1/commands/set_brightness", {"level": level})

    def set_enabled(self, enabled: bool) -> dict[str, Any]:
        return self._request_json("POST", "/api/v1/commands/set_enabled", {"enabled": enabled})

    def activate_preset(self, preset_id: str, spec: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request_json("POST", f"/api/v1/presets/{preset_id}/activate", {"spec": spec or {}})

    def close(self, *, force: bool = False, wait_timeout: float = 10.0) -> None:
        process = self.process
        if process is None:
            return
        if process.poll() is None and not force:
            try:
                self.shutdown()
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

    def _read_active_service_file(self) -> dict[str, Any] | None:
        state_file = self.runtime_state_file
        if not state_file.exists():
            return None
        try:
            payload = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("host") and payload.get("port"):
            return payload
        return None

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload, ensure_ascii=True).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=self.request_timeout) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8") if exc.fp is not None else ""
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"Controller request failed: {exc}") from exc
        if not body:
            return {}
        return json.loads(body)


__all__ = ["LedControllerRelease1"]