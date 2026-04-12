from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request


@dataclass(slots=True)
class ClientCallResult:
    ok: bool
    status_code: int | None = None
    data: Any = None
    error: str | None = None


class LocalControllerClient:
    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8765,
        timeout: float = 2.0,
        best_effort: bool = True,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.timeout = float(timeout)
        self.best_effort = best_effort

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def ping(self) -> ClientCallResult:
        return self._request_json("GET", "/api/v1/ping")

    def get_status(self) -> ClientCallResult:
        return self._request_json("GET", "/api/v1/status")

    def list_effects(self) -> ClientCallResult:
        return self._request_json("GET", "/api/v1/effects")

    def list_effects_for_source(self, source_id: str) -> ClientCallResult:
        return self._request_json("GET", f"/api/v1/effects/{source_id}")

    def get_effect(self, source_id: str, effect_id: str) -> ClientCallResult:
        return self._request_json("GET", f"/api/v1/effects/{source_id}/{effect_id}")

    def list_effect_presets(self, source_id: str, effect_id: str) -> ClientCallResult:
        return self._request_json("GET", f"/api/v1/effects/{source_id}/{effect_id}/presets")

    def list_effect_commands_for_effect(self, source_id: str, effect_id: str) -> ClientCallResult:
        return self._request_json("GET", f"/api/v1/effects/{source_id}/{effect_id}/commands")

    def apply_effect_for_source(
        self,
        source_id: str,
        effect_id: str,
        target_layer: str,
        params: dict[str, Any] | None = None,
        *,
        duration_ms: int | None = None,
        priority: int | None = None,
        enqueue: bool = False,
        replace_existing: bool = True,
    ) -> ClientCallResult:
        return self._request_json(
            "POST",
            f"/api/v1/effects/{source_id}/{effect_id}/apply",
            {
                "target_layer": target_layer,
                "params": params or {},
                "duration_ms": duration_ms,
                "priority": priority,
                "enqueue": enqueue,
                "replace_existing": replace_existing,
            },
        )

    def get_effect_preset(self, source_id: str, preset_id: str) -> ClientCallResult:
        return self._request_json("GET", f"/api/v1/effect-presets/{source_id}/{preset_id}")

    def apply_effect_preset(self, source_id: str, preset_id: str) -> ClientCallResult:
        return self._request_json("POST", f"/api/v1/effect-presets/{source_id}/{preset_id}/apply")

    def list_effect_sources(self) -> ClientCallResult:
        return self._request_json("GET", "/api/v1/effect-sources")

    def register_effect_source(self, path: str, *, enabled: bool = True) -> ClientCallResult:
        return self._request_json("POST", "/api/v1/effect-sources/register", {"path": path, "enabled": enabled})

    def reload_effect_sources(self) -> ClientCallResult:
        return self._request_json("POST", "/api/v1/effect-sources/reload")

    def remove_effect_source(self, source_id: str) -> ClientCallResult:
        return self._request_json("DELETE", f"/api/v1/effect-sources/{source_id}")

    def list_commands(self, source_id: str | None = None) -> ClientCallResult:
        path = "/api/v1/commands" if source_id is None else f"/api/v1/commands/{source_id}"
        return self._request_json("GET", path)

    def get_command(self, source_id: str, command_name: str) -> ClientCallResult:
        return self._request_json("GET", f"/api/v1/commands/{source_id}/{command_name}")

    def invoke_command(self, source_id: str, command_name: str, state: str | None = None) -> ClientCallResult:
        path = f"/api/v1/commands/{source_id}/{command_name}"
        if state is not None:
            path = f"{path}/{state}"
        return self._request_json("POST", path)

    def set_state(self, state_name: str, payload: dict[str, Any] | None = None) -> ClientCallResult:
        return self._request_json("POST", "/api/v1/commands/set_state", {"state_name": state_name, "payload": payload or {}})

    def clear_state(self, state_name: str | None = None) -> ClientCallResult:
        return self._request_json("POST", "/api/v1/commands/clear_state", {"state_name": state_name})

    def emit_event(self, event_name: str, payload: dict[str, Any] | None = None) -> ClientCallResult:
        return self._request_json("POST", "/api/v1/commands/emit_event", {"event_name": event_name, "payload": payload or {}})

    def reset(self) -> ClientCallResult:
        return self._request_json("POST", "/api/v1/commands/reset")

    def shutdown(self) -> ClientCallResult:
        return self._request_json("POST", "/api/v1/commands/shutdown")

    def start_timeout_countdown(
        self,
        total_ms: int,
        remaining_ms: int | None = None,
        *,
        follow_up_state: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ClientCallResult:
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

    def update_timeout_countdown(self, remaining_ms: int) -> ClientCallResult:
        return self._request_json("POST", "/api/v1/commands/update_timeout_countdown", {"remaining_ms": remaining_ms})

    def cancel_timeout_countdown(self) -> ClientCallResult:
        return self._request_json("POST", "/api/v1/commands/cancel_timeout_countdown")

    def set_direction(self, direction_deg: float) -> ClientCallResult:
        return self._request_json("POST", "/api/v1/commands/set_direction", {"direction_deg": direction_deg})

    def clear_direction(self) -> ClientCallResult:
        return self._request_json("POST", "/api/v1/commands/clear_direction")

    def set_brightness(self, level: float) -> ClientCallResult:
        return self._request_json("POST", "/api/v1/commands/set_brightness", {"level": level})

    def set_enabled(self, enabled: bool) -> ClientCallResult:
        return self._request_json("POST", "/api/v1/commands/set_enabled", {"enabled": enabled})

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
    ) -> ClientCallResult:
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

    def clear_layer(self, target_layer: str) -> ClientCallResult:
        return self._request_json("POST", "/api/v1/commands/clear_layer", {"target_layer": target_layer})

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> ClientCallResult:
        url = f"{self.base_url}{path}"
        data = None if payload is None else json.dumps(payload, ensure_ascii=True).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                parsed = None if not body else json.loads(body)
                return ClientCallResult(ok=True, status_code=response.status, data=parsed)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8") if exc.fp is not None else ""
            parsed = None
            if body:
                try:
                    parsed = json.loads(body)
                except json.JSONDecodeError:
                    parsed = body
            return self._handle_error(exc, exc.code, parsed)
        except (error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
            return self._handle_error(exc, None, None)

    def _handle_error(self, exc: Exception, status_code: int | None, data: Any) -> ClientCallResult:
        result = ClientCallResult(ok=False, status_code=status_code, data=data, error=str(exc))
        if self.best_effort:
            return result
        raise RuntimeError(result.error or "Controller request failed") from exc
