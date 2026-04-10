from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

from ..integrations.adapters import ConsolePreviewAdapter, FrameAdapter, ReSpeakerAdapter
from ..infrastructure.background_state_store import load_background_state, save_background_state
from ..core.effect_schema import parse_layer_id
from ..infrastructure.logging_utils import get_logger
from ..infrastructure.paths import BACKGROUND_STATE_FILE
from ..engine.preset_loader import PresetRegistry
from ..engine.runtime import ControllerRuntime
from ..core.models import Frame, LED_COUNT


logger = get_logger("service")


class ControllerService:
    def __init__(
        self,
        *,
        fps: float = 8.0,
        use_device: bool = True,
        preset_registry: PresetRegistry | None = None,
        adapter_factory: Callable[[], FrameAdapter] | None = None,
        background_state_file: str | Path | None = None,
        signal_on_s: float = 0.06,
        signal_off_s: float = 0.04,
    ) -> None:
        self.fps = max(1.0, float(fps))
        self.preset_registry = preset_registry or PresetRegistry.empty()
        self.background_state_file = Path(background_state_file or BACKGROUND_STATE_FILE)
        self.signal_on_s = max(0.0, float(signal_on_s))
        self.signal_off_s = max(0.0, float(signal_off_s))
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
        self._background_state_signature: str | None = None

        self._restore_background_state()
        logger.info(
            "controller service initialized output_mode=%s requested_output_mode=%s fallback_active=%s",
            self.output_mode,
            self.requested_output_mode,
            self.fallback_active,
        )

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
            return (
                ConsolePreviewAdapter(show_timestamp=False, emit_output=True, emit_only_on_change=True),
                "console-preview",
                False,
                False,
                None,
            )

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
        self._emit_service_signal(0x00FF00)
        self._thread = threading.Thread(target=self._render_loop, name="controller-service-render", daemon=True)
        self._thread.start()
        logger.info("controller service started fps=%s", self.fps)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        with self._lock:
            if self._started_at is not None:
                self._emit_service_signal(0xFF0000)
            self.runtime.close()
        self._thread = None
        self._started_at = None
        logger.info("controller service stopped")

    def _render_once_locked(self, now: float | None = None) -> None:
        self.runtime.render_once(time.monotonic() if now is None else now)
        self._sync_background_state_storage()
        self._render_count += 1

    def _restore_background_state(self) -> None:
        persisted_state = load_background_state(self.background_state_file)
        if persisted_state is not None:
            try:
                self.runtime.restore_persisted_background_state(persisted_state)
                logger.info("restored persisted background state from %s", self.background_state_file)
            except Exception:
                logger.exception("failed to restore persisted background state from %s", self.background_state_file)
                self.runtime.apply_default_background_state()
        else:
            self.runtime.apply_default_background_state()
            logger.info("applied default background fallback because no persisted background state was found")
        self._sync_background_state_storage(force=True)

    def _sync_background_state_storage(self, *, force: bool = False) -> None:
        current_signature = self.runtime.background_state_signature()
        if not force and current_signature == self._background_state_signature:
            return

        disposition, persisted_state = self.runtime.background_state_persistence_snapshot()
        if disposition == "persistable":
            save_background_state(self.background_state_file, persisted_state)
        elif disposition == "empty":
            save_background_state(self.background_state_file, None)

        self._background_state_signature = current_signature

    def _render_loop(self) -> None:
        interval = 1.0 / self.fps
        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                with self._lock:
                    self._render_once_locked(started)
            except Exception as exc:
                self._last_error = repr(exc)
                logger.exception("render loop iteration failed")
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
        logger.info("shutdown requested")
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

    def list_effects(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for effect_id in self.runtime.effect_registry.list_effect_ids():
            registered = self.runtime.effect_registry.get(effect_id)
            definition = registered.definition
            items.append(
                {
                    "id": definition.id,
                    "qualified_id": registered.qualified_effect_id,
                    "title": definition.title,
                    "description": definition.description,
                    "source_id": registered.source_id,
                    "source_kind": registered.source_kind,
                    "package_id": registered.package_id,
                    "package_version": registered.package_version,
                    "defaults": dict(definition.defaults),
                    "tags": list(definition.tags),
                    "supported_layers": [
                        layer_id.value for layer_id, rule in definition.layer_rules.items() if rule.allowed
                    ],
                    "parameters": {
                        name: {
                            "type": param.type,
                            "required": param.required,
                            "default": param.default,
                            "description": param.description,
                            "minimum": param.minimum,
                            "maximum": param.maximum,
                            "enum_values": list(param.enum_values),
                            "unit": param.unit,
                        }
                        for name, param in definition.parameter_schema.items()
                    },
                }
            )
        return items

    def list_effect_sources(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._serialize_effect_source(source) for source in self.runtime.effect_registry.list_effect_sources()]

    def register_effect_source(self, path: str, *, enabled: bool = True) -> dict[str, Any]:
        with self._lock:
            source = self.runtime.effect_registry.register_effect_source(path, enabled=enabled)
            return {"source": self._serialize_effect_source(source), "items": self.list_effect_sources()}

    def reload_effect_sources(self) -> dict[str, Any]:
        with self._lock:
            self.runtime.effect_registry.reload()
            return {"items": [self._serialize_effect_source(source) for source in self.runtime.effect_registry.list_effect_sources()]}

    def remove_effect_source(self, source_id: str) -> dict[str, Any]:
        with self._lock:
            self.runtime.effect_registry.remove_source(source_id)
            return {"items": [self._serialize_effect_source(source) for source in self.runtime.effect_registry.list_effect_sources()]}

    def list_effect_commands(self, source_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            return self.runtime.effect_registry.list_effect_commands(source_id)

    def effect_command_info(self, source_id: str, command_name: str) -> dict[str, Any]:
        with self._lock:
            return self.runtime.effect_registry.get_command(source_id, command_name).serialize()

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
        layer_id = parse_layer_id(target_layer)
        effect_params = dict(params or {})
        return self._mutate(
            lambda: self.runtime.apply_effect(
                effect_id,
                layer_id,
                effect_params,
                duration_ms=duration_ms,
                priority=priority,
                enqueue=enqueue,
                replace_existing=replace_existing,
                scene_name=f"manual:{layer_id.value.lower()}:{effect_id}",
                item_id=f"manual:{effect_id}",
                mode=effect_id,
                payload=effect_params,
            )
        )

    def clear_layer(self, target_layer: str) -> dict[str, Any]:
        layer_id = parse_layer_id(target_layer)
        return self._mutate(lambda: self.runtime.clear_layer(layer_id))

    def invoke_effect_command(self, source_id: str, command_name: str, state: str | None = None) -> dict[str, Any]:
        command = self.runtime.effect_registry.get_command(source_id, command_name)
        desired_state = self._resolve_command_state(command, state)
        return self._mutate(lambda: self._apply_effect_command(command, desired_state))

    def _apply_effect_command(self, command, desired_state: str) -> None:
        action = command.on_action if desired_state == "on" else command.off_action
        if action is None:
            raise ValueError(f"Command {command.command_name!r} does not support state {desired_state!r}")
        if action.action == "clear_layer":
            self.runtime.clear_layer(action.target_layer)
            return

        params = dict(action.params)
        params["__command_source_id"] = command.source_id
        params["__command_name"] = command.command_name
        self.runtime.apply_effect(
            action.effect_id,
            action.target_layer,
            params,
            replace_existing=action.replace_existing,
            scene_name=f"command:{command.source_id}:{command.command_name}",
            item_id=f"command:{command.source_id}:{command.command_name}",
            mode=command.command_name,
            payload={"source_id": command.source_id, "command_name": command.command_name},
            valid=True,
        )

    def _resolve_command_state(self, command, requested_state: str | None) -> str:
        if requested_state is not None:
            normalized = str(requested_state).strip().lower()
            if normalized not in {"on", "off"}:
                raise ValueError(f"Unsupported command state: {requested_state!r}")
            if normalized == "off" and command.off_action is None:
                raise ValueError(f"Command {command.command_name!r} does not support 'off'")
            return normalized

        if command.kind == "state_toggle":
            if self.runtime.is_command_active(command.source_id, command.command_name, command.on_action.target_layer):
                return "off"
        return "on"

    def _serialize_effect_source(self, source) -> dict[str, Any]:
        return {
            "source_id": source.source_id,
            "path": source.path,
            "kind": source.kind,
            "enabled": source.enabled,
            "autodiscovered": source.autodiscovered,
            "package_id": source.package_id,
            "package_version": source.package_version,
            "command_count": source.command_count,
        }

    def _emit_service_signal(self, color: int) -> None:
        on_frame = Frame(leds=[int(color)] * LED_COUNT, timestamp=time.time())
        off_frame = Frame(leds=[0] * LED_COUNT, timestamp=time.time())
        for _ in range(3):
            self.adapter.apply_frame(on_frame)
            if self.signal_on_s > 0.0:
                time.sleep(self.signal_on_s)
            self.adapter.apply_frame(off_frame)
            if self.signal_off_s > 0.0:
                time.sleep(self.signal_off_s)


ControllerApiService = ControllerService
