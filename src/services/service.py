from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Callable

from ..integrations.adapters import (
    ConsolePreviewAdapter,
    DoAInputAdapter,
    FrameAdapter,
    ReSpeakerAdapter,
)
from ..infrastructure.background_state_store import load_background_state, save_background_state
from ..core.effect_schema import DefinitionType
from ..infrastructure.logging_utils import get_logger
from ..infrastructure.paths import BACKGROUND_STATE_FILE
from ..engine.input_provider import PolledInputProvider
from ..engine.runtime import ControllerRuntime
from ..core.models import Frame, LED_COUNT


logger = get_logger("service")


class ControllerService:
    def __init__(
        self,
        *,
        fps: float = 8.0,
        use_device: bool = True,
        adapter_factory: Callable[[], FrameAdapter] | None = None,
        background_state_file: str | Path | None = None,
        signal_on_s: float = 0.06,
        signal_off_s: float = 0.04,
    ) -> None:
        self.fps = max(1.0, float(fps))
        self.background_state_file = Path(background_state_file or BACKGROUND_STATE_FILE)
        self.signal_on_s = max(0.0, float(signal_on_s))
        self.signal_off_s = max(0.0, float(signal_off_s))
        self.requested_output_mode = "device" if use_device else "console-preview"
        self.adapter, self.output_mode, self.device_available, self.fallback_active, self._adapter_error = self._build_adapter(
            use_device=use_device,
            adapter_factory=adapter_factory,
        )
        self._hardware_input_providers: dict[str, PolledInputProvider] = {}
        if isinstance(self.adapter, DoAInputAdapter):
            self._hardware_input_providers["respeaker_doa"] = PolledInputProvider(
                "respeaker_doa",
                self.adapter.read_doa_inputs,
                max_hz=30.0,
            )
        self.runtime = ControllerRuntime(
            adapter=self.adapter,
            input_providers={
                provider_id: provider.sample
                for provider_id, provider in self._hardware_input_providers.items()
            },
        )
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
        resolved_now = time.monotonic() if now is None else now
        self._refresh_hardware_inputs(resolved_now)
        self.runtime.render_once(resolved_now)
        self._sync_background_state_storage()
        self._render_count += 1

    def _refresh_hardware_inputs(self, now: float) -> None:
        for provider in self._hardware_input_providers.values():
            previous_error = provider.last_error
            attempted = provider.refresh(now)
            if not attempted:
                continue
            current_error = provider.last_error
            if current_error is not None and current_error != previous_error:
                logger.warning(
                    "hardware input polling failed provider=%s error=%s",
                    provider.provider_id,
                    current_error,
                )
            elif current_error is None and previous_error is not None:
                logger.info(
                    "hardware input polling recovered provider=%s",
                    provider.provider_id,
                )

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
                "hardware_inputs": {
                    provider_id: provider.status(time.monotonic())
                    for provider_id, provider in self._hardware_input_providers.items()
                },
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

    def set_direction(self, direction: float) -> dict[str, Any]:
        return self._mutate(lambda: self.runtime.set_direction(direction))

    def clear_direction(self) -> dict[str, Any]:
        return self._mutate(self.runtime.clear_direction)

    def set_brightness(self, level: float) -> dict[str, Any]:
        return self._mutate(lambda: self.runtime.set_brightness(level))

    def set_enabled(self, enabled: bool) -> dict[str, Any]:
        return self._mutate(lambda: self.runtime.set_enabled(enabled))

    def list_effects(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._serialize_registered_effect(effect) for effect in self.runtime.effect_registry.list_registered_effects()]

    def list_definitions(
        self,
        definition_type: DefinitionType,
        *,
        details: bool = False,
    ) -> list[str] | list[dict[str, Any]]:
        with self._lock:
            effects = [
                effect
                for effect in self.runtime.effect_registry.list_registered_effects()
                if effect.definition.definition_type is definition_type
            ]
            if not details:
                return [effect.local_effect_id for effect in effects]
            return [self._serialize_definition_v2(effect) for effect in effects]

    def list_presets_v2(
        self,
        definition_type: DefinitionType | None = None,
        *,
        details: bool = False,
    ) -> list[str] | list[dict[str, Any]]:
        with self._lock:
            presets = self.runtime.effect_registry.list_effect_presets()
            if definition_type is not None:
                presets = [
                    preset
                    for preset in presets
                    if self.runtime.effect_registry.get_for_source(
                        preset["source_id"],
                        preset["effect_id"],
                    ).definition.definition_type
                    is definition_type
                ]
            if details:
                return presets
            return [preset["preset_id"] for preset in presets]

    def target_info(self, target: str) -> dict[str, Any]:
        with self._lock:
            resolved = self.runtime.effect_registry.resolve_target(target)
            payload = self._serialize_definition_v2(resolved.effect)
            payload["resolved_from"] = target
            payload["resolved_kind"] = resolved.kind
            if resolved.preset_id is not None:
                payload["preset"] = {
                    "id": resolved.preset_id,
                    "config": dict(resolved.preset_params or {}),
                }
            return payload

    def set_state_target(
        self,
        target: str,
        config: dict[str, Any] | None = None,
        *,
        slot: str = "primary",
        action: str = "on",
    ) -> dict[str, Any]:
        snapshot = self._mutate(
            lambda: self.runtime.set_state_target(target, config, slot=slot, action=action)
        )
        return {
            "ok": True,
            "operation": "set",
            "type": "state",
            "target": target,
            "slot": slot,
            "action": action,
            "status": snapshot,
        }

    def clear_state_target(self, *, slot: str = "primary") -> dict[str, Any]:
        snapshot = self._mutate(lambda: self.runtime.clear_state_target(slot=slot))
        return {
            "ok": True,
            "operation": "clear",
            "type": "state",
            "slot": slot,
            "status": snapshot,
        }

    def set_overlay_target(
        self,
        target: str,
        channel: str | None = None,
        config: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        *,
        action: str = "on",
    ) -> dict[str, Any]:
        snapshot = self._mutate(
            lambda: self.runtime.set_overlay(
                target,
                channel,
                config,
                inputs,
                action=action,
            )
        )
        return {
            "ok": True,
            "operation": "set",
            "type": "overlay",
            "target": target,
            "channel": channel,
            "action": action,
            "status": snapshot,
        }

    def update_overlay_target(self, channel: str, inputs: dict[str, Any]) -> dict[str, Any]:
        snapshot = self._mutate(lambda: self.runtime.update_overlay(channel, inputs))
        return {
            "ok": True,
            "operation": "update",
            "type": "overlay",
            "channel": channel,
            "status": snapshot,
        }

    def clear_overlay_target(self, channel: str) -> dict[str, Any]:
        snapshot = self._mutate(lambda: self.runtime.clear_overlay(channel))
        return {
            "ok": True,
            "operation": "clear",
            "type": "overlay",
            "channel": channel,
            "status": snapshot,
        }

    def emit_event_target(
        self,
        target: str,
        config: dict[str, Any] | None = None,
        *,
        priority: int | None = None,
    ) -> dict[str, Any]:
        snapshot = self._mutate(
            lambda: self.runtime.emit_event_target(target, config, priority=priority)
        )
        return {
            "ok": True,
            "operation": "emit",
            "type": "event",
            "target": target,
            "status": snapshot,
        }

    def list_effects_for_source(self, source_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [
                self._serialize_registered_effect(effect)
                for effect in self.runtime.effect_registry.list_registered_effects(source_id)
            ]

    def effect_info(self, effect_id: str) -> dict[str, Any]:
        with self._lock:
            return self._serialize_registered_effect(self.runtime.effect_registry.get(effect_id))

    def effect_info_for_source(self, source_id: str, effect_id: str) -> dict[str, Any]:
        with self._lock:
            return self._serialize_registered_effect(self.runtime.effect_registry.get_for_source(source_id, effect_id))

    def list_effect_presets(self, source_id: str | None = None, effect_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            return self.runtime.effect_registry.list_effect_presets(source_id, effect_id)

    def effect_preset_info(self, source_id: str, preset_id: str) -> dict[str, Any]:
        with self._lock:
            return self.runtime.effect_registry.get_preset(source_id, preset_id).serialize()

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

    def _serialize_registered_effect(self, registered) -> dict[str, Any]:
        definition = registered.definition
        return {
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
                    "nullable": param.nullable,
                    "aliases": list(param.aliases),
                }
                for name, param in definition.parameter_schema.items()
            },
        }

    def _serialize_definition_v2(self, registered) -> dict[str, Any]:
        definition = registered.definition
        return {
            "id": definition.id,
            "qualified_id": registered.qualified_effect_id,
            "source_id": registered.source_id,
            "package_id": registered.package_id,
            "type": definition.definition_type.value,
            "overlay_mode": (
                None if definition.overlay_mode is None else definition.overlay_mode.value
            ),
            "title": definition.title,
            "description": definition.description,
            "version": definition.version,
            "defaults": dict(definition.defaults),
            "parameters": {
                name: self._serialize_parameter(param)
                for name, param in definition.parameter_schema.items()
            },
            "runtime_inputs": {
                name: self._serialize_parameter(param)
                for name, param in definition.runtime_input_schema.items()
            },
            "visual": {
                "color_model": definition.color_model.value,
                "composition": definition.composition.value,
                "animated": definition.animated,
                "directional": definition.directional,
            },
            "input_sampling": self._serialize_input_sampling(definition),
            "tags": list(definition.tags),
        }

    def _serialize_parameter(self, param) -> dict[str, Any]:
        return {
            "type": param.type,
            "required": param.required,
            "default": param.default,
            "description": param.description,
            "minimum": param.minimum,
            "maximum": param.maximum,
            "enum_values": list(param.enum_values),
            "unit": param.unit,
            "nullable": param.nullable,
            "aliases": list(param.aliases),
        }

    def _serialize_input_sampling(self, definition) -> dict[str, Any] | None:
        policy = definition.effective_input_sampling()
        if policy is None:
            return None
        return {
            "mode": policy.mode.value,
            "provider_id": policy.provider_id,
            "interval_ms": policy.interval_ms,
            "heartbeat_interval_ms": policy.heartbeat_interval_ms,
            "max_missed_heartbeats": policy.max_missed_heartbeats,
            "failure_after_ms": policy.failure_after_ms,
        }

    def _serialize_effect_source(self, source) -> dict[str, Any]:
        return {
            "source_id": source.source_id,
            "path": source.path,
            "kind": source.kind,
            "enabled": source.enabled,
            "autodiscovered": source.autodiscovered,
            "package_id": source.package_id,
            "package_version": source.package_version,
            "preset_count": source.preset_count,
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
