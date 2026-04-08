from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

from .adapters import ConsolePreviewAdapter, FrameAdapter, ReSpeakerAdapter
from .preset_loader import PresetRegistry
from .runtime import ControllerRuntime


class ControllerService:
    def __init__(
        self,
        *,
        fps: float = 8.0,
        use_device: bool = True,
        preset_registry: PresetRegistry | None = None,
        adapter_factory: Callable[[], FrameAdapter] | None = None,
    ) -> None:
        self.fps = max(1.0, float(fps))
        self.preset_registry = preset_registry or PresetRegistry.empty()
        self.requested_output_mode = "device" if use_device else "console-preview"
        self.adapter, self.output_mode, self.device_available, self.fallback_active, self._adapter_error = self._build_adapter(
            use_device=use_device,
            adapter_factory=adapter_factory,
        )
        self.runtime = ControllerRuntime(adapter=self.adapter, preset_registry=self.preset_registry)
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._render_count = 0
        self._last_error: str | None = self._adapter_error
        self._started_at: float | None = None
        self._shutdown_callback: Callable[[], None] | None = None

        if self.fallback_active and use_device:
            self.runtime.set_state(
                "offline",
                payload={"reason": "device_unavailable", "error": self._adapter_error},
            )

    def _build_adapter(
        self,
        *,
        use_device: bool,
        adapter_factory: Callable[[], FrameAdapter] | None,
    ) -> tuple[FrameAdapter, str, bool, bool, str | None]:
        if adapter_factory is not None:
            try:
                return adapter_factory(), self.requested_output_mode, use_device, False, None
            except Exception as exc:
                fallback = ConsolePreviewAdapter(show_timestamp=False, emit_output=False)
                return fallback, "console-preview", False, True, repr(exc)

        if not use_device:
            return ConsolePreviewAdapter(show_timestamp=False, emit_output=False), "console-preview", False, False, None

        try:
            return ReSpeakerAdapter(), "device", True, False, None
        except Exception as exc:
            fallback = ConsolePreviewAdapter(show_timestamp=False, emit_output=False)
            return fallback, "console-preview", False, True, repr(exc)

    def set_shutdown_callback(self, callback: Callable[[], None] | None) -> None:
        self._shutdown_callback = callback

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._started_at = time.time()
        self._thread = threading.Thread(target=self._render_loop, name="controller-service-render", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        with self._lock:
            self.runtime.close()

    def _render_once_locked(self, now: float | None = None) -> None:
        self.runtime.render_once(time.monotonic() if now is None else now)
        self._render_count += 1

    def _render_loop(self) -> None:
        interval = 1.0 / self.fps
        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                with self._lock:
                    self._render_once_locked(started)
            except Exception as exc:
                self._last_error = repr(exc)
            elapsed = time.monotonic() - started
            self._stop_event.wait(max(0.0, interval - elapsed))

    def _mutate(self, action: Callable[[], None]) -> dict[str, Any]:
        with self._lock:
            action()
            self._render_once_locked()
            return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            snapshot = self.runtime.get_status()
        snapshot.update(
            {
                "render_loop_running": self._thread is not None and self._thread.is_alive(),
                "fps": self.fps,
                "render_count": self._render_count,
                "started_at": self._started_at,
                "last_error": self._last_error,
                "requested_output_mode": self.requested_output_mode,
                "output_mode": self.output_mode,
                "device_available": self.device_available,
                "fallback_active": self.fallback_active,
            }
        )
        return snapshot

    def ping(self) -> dict[str, Any]:
        return {
            "ok": True,
            "render_loop_running": self._thread is not None and self._thread.is_alive(),
            "output_mode": self.output_mode,
            "timestamp": time.time(),
        }

    def get_status(self) -> dict[str, Any]:
        return self.snapshot()

    def set_state(self, state_name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._mutate(lambda: self.runtime.set_state(state_name, payload))

    def clear_state(self, state_name: str | None = None) -> dict[str, Any]:
        return self._mutate(lambda: self.runtime.clear_state(state_name))

    def emit_event(self, event_name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._mutate(lambda: self.runtime.emit_event(event_name, payload))

    def reset(self) -> dict[str, Any]:
        return self._mutate(lambda: self.runtime.reset(initial_state="idle"))

    def shutdown(self) -> dict[str, Any]:
        snapshot = self._mutate(lambda: self.runtime.set_state("service_stopping", {"reason": "shutdown"}))
        self._stop_event.set()
        if self._shutdown_callback is not None:
            threading.Thread(target=self._shutdown_callback, daemon=True).start()
        return snapshot

    def start_timeout_countdown(
        self,
        total_ms: int,
        remaining_ms: int | None = None,
        *,
        follow_up_state: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._mutate(
            lambda: self.runtime.start_timeout_countdown(
                total_ms,
                remaining_ms,
                follow_up_state=follow_up_state,
                payload=payload,
            )
        )

    def update_timeout_countdown(self, remaining_ms: int) -> dict[str, Any]:
        return self._mutate(lambda: self.runtime.update_timeout_countdown(remaining_ms))

    def cancel_timeout_countdown(self) -> dict[str, Any]:
        return self._mutate(self.runtime.cancel_timeout_countdown)

    def set_direction(self, direction_deg: float) -> dict[str, Any]:
        return self._mutate(lambda: self.runtime.set_direction(direction_deg))

    def clear_direction(self) -> dict[str, Any]:
        return self._mutate(self.runtime.clear_direction)

    def set_brightness(self, level: float) -> dict[str, Any]:
        return self._mutate(lambda: self.runtime.set_brightness(level))

    def set_enabled(self, enabled: bool) -> dict[str, Any]:
        return self._mutate(lambda: self.runtime.set_enabled(enabled))

    def list_presets(self) -> list[dict[str, Any]]:
        return [self.preset_info(preset.manifest.preset_id) for preset in self.preset_registry.list_presets()]

    def preset_info(self, preset_id: str) -> dict[str, Any]:
        preset = self.preset_registry.get_by_id(preset_id)
        sample = None if preset.sample_path is None else str(preset.sample_path)
        return {
            "id": preset.manifest.preset_id,
            "name": preset.manifest.name,
            "description": preset.manifest.description,
            "command": preset.manifest.command,
            "target_layer": preset.manifest.target_layer,
            "supports_cli": preset.manifest.supports_cli,
            "supports_api": preset.manifest.supports_api,
            "tags": list(preset.manifest.tags),
            "sample_spec_path": sample,
        }

    def preset_sample(self, preset_id: str) -> dict[str, Any]:
        preset = self.preset_registry.get_by_id(preset_id)
        if preset.sample_path is None:
            raise FileNotFoundError(f"Preset {preset_id} does not define a sample spec")
        return json.loads(Path(preset.sample_path).read_text(encoding="utf-8"))

    def activate_preset(self, preset_id: str, spec: dict[str, Any]) -> dict[str, Any]:
        return self._mutate(lambda: self.runtime.apply_preset(preset_id, spec))


ControllerApiService = ControllerService