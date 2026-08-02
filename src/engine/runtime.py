from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from ..integrations.adapters import ConsolePreviewAdapter, FrameAdapter
from .composer import SceneComposer
from .effect_registry import EffectRegistry, build_default_effect_registry
from ..core.effect_schema import (
    CommandKind,
    DefinitionType,
    LayerId,
    NormalizedCommand,
    OverlayMode,
    PersistedLayerState,
)
from ..core.parameter_validation import normalize_runtime_inputs, resolve_configuration
from ..core.layers import LayerStore
from ..core.models import BaseState, CountdownState, Frame, Scene
from ..integrations.application_commands import (
    ControllerCommandNormalizer,
    build_effect_invocation,
    canonicalize_effect_params,
)
from .renderer import SceneRenderer


TickCallback = Callable[["ControllerRuntime", float], None]
_NON_PERSISTENT_BACKGROUND_MODES = {"offline", "service_starting", "service_stopping"}


def _normalize_name(value: str, fallback: str) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    return text or fallback


def _copy_payload(payload: dict | None) -> dict:
    return dict(payload or {})


def _timestamp_or_now(timestamp: float | None) -> float:
    return time.monotonic() if timestamp is None else float(timestamp)


def _public_params(params: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if not str(key).startswith("__")}


class ControllerRuntime:
    def __init__(
        self,
        adapter: FrameAdapter | None = None,
        effect_registry: EffectRegistry | None = None,
        input_providers: dict[str, Callable] | None = None,
    ) -> None:
        self.effect_registry = effect_registry or build_default_effect_registry()
        self.normalizer = ControllerCommandNormalizer()
        self.store = LayerStore()
        self.composer = SceneComposer(self.effect_registry, input_providers=input_providers)
        self.renderer = SceneRenderer()
        self.adapter = adapter or ConsolePreviewAdapter()
        self.last_scene: Scene | None = None
        self.last_frame: Frame | None = None
        self._expire_callbacks: dict[str, Callable[[float], None]] = {}
        self._invocation_sequence = 0
        self._countdown_invocation_id: str | None = None
        self.reset(initial_state="idle")

    def set_state(self, state_name: str, payload: dict | None = None, *, timestamp: float | None = None) -> None:
        now = _timestamp_or_now(timestamp)
        name = _normalize_name(state_name, "idle")
        copied_payload = _copy_payload(payload)
        self.store.base_state = BaseState(name=name, payload=copied_payload, updated_at=now)
        self._apply_normalized_commands(
            self.normalizer.normalize_set_state(name, copied_payload, timestamp=now),
            timestamp=now,
        )

    def clear_state(self, state_name: str | None = None, *, timestamp: float | None = None) -> None:
        normalized = None if state_name is None else _normalize_name(state_name, "")
        if normalized and normalized != self.store.base_state.name:
            return
        self.set_state("idle", timestamp=timestamp)

    def emit_event(self, event_name: str, payload: dict | None = None, *, timestamp: float | None = None):
        now = _timestamp_or_now(timestamp)
        commands = self.normalizer.normalize_emit_event(event_name, _copy_payload(payload), timestamp=now)
        applied = self._apply_normalized_commands(commands, timestamp=now)
        return None if not applied else applied[0]

    def start_timeout_countdown(
        self,
        total_ms: int,
        remaining_ms: int | None = None,
        *,
        follow_up_state: str | None = None,
        payload: dict | None = None,
        timestamp: float | None = None,
    ) -> None:
        now = _timestamp_or_now(timestamp)
        total_ms = max(1, int(total_ms))
        remaining_ms = total_ms if remaining_ms is None else max(0, min(int(remaining_ms), total_ms))
        copied_payload = _copy_payload(payload)
        normalized_follow_up = None if follow_up_state is None else _normalize_name(follow_up_state, "")
        self.store.countdown = CountdownState(
            total_ms=total_ms,
            remaining_ms=remaining_ms,
            started_at=now,
            deadline=now + (remaining_ms / 1000.0),
            follow_up_state=normalized_follow_up,
            payload=copied_payload,
        )
        applied = self._apply_normalized_commands(
            self.normalizer.normalize_start_timeout_countdown(
                total_ms,
                remaining_ms,
                follow_up_state=normalized_follow_up,
                payload=copied_payload,
                timestamp=now,
            ),
            timestamp=now,
        )
        if applied:
            self._countdown_invocation_id = applied[0].invocation_id
            self._expire_callbacks[applied[0].invocation_id] = self._countdown_expire_callback(
                applied[0].invocation_id,
                normalized_follow_up,
            )

    def update_timeout_countdown(self, remaining_ms: int, *, timestamp: float | None = None) -> None:
        if self.store.countdown is None:
            raise ValueError("No active countdown")
        now = _timestamp_or_now(timestamp)
        self.store.countdown.remaining_ms = max(0, min(int(remaining_ms), self.store.countdown.total_ms))
        self.store.countdown.started_at = now
        self.store.countdown.deadline = now + (self.store.countdown.remaining_ms / 1000.0)
        self.store.countdown.active = True
        applied = self._apply_normalized_commands(
            self.normalizer.normalize_start_timeout_countdown(
                self.store.countdown.total_ms,
                self.store.countdown.remaining_ms,
                follow_up_state=self.store.countdown.follow_up_state,
                payload=self.store.countdown.payload,
                source="runtime.update_timeout_countdown",
                timestamp=now,
            ),
            timestamp=now,
        )
        if applied:
            self._countdown_invocation_id = applied[0].invocation_id
            self._expire_callbacks[applied[0].invocation_id] = self._countdown_expire_callback(
                applied[0].invocation_id,
                self.store.countdown.follow_up_state,
            )

    def cancel_timeout_countdown(self) -> None:
        self.store.countdown = None
        self._countdown_invocation_id = None
        self._clear_layer(LayerId.TEMP_OVERLAY_LAYER)

    def set_direction(self, direction: float) -> None:
        normalized = float(direction) % 360.0
        self.store.direction = normalized
        now = time.monotonic()
        self._apply_normalized_commands(
            self.normalizer.normalize_set_direction(normalized, timestamp=now),
            timestamp=now,
        )

    def clear_direction(self) -> None:
        self.store.direction = None
        self._clear_layer(LayerId.ONGOING_OVERLAY_LAYER)

    def set_brightness(self, level: float) -> None:
        self.store.brightness = max(0.0, min(1.0, float(level)))

    def set_enabled(self, enabled: bool) -> None:
        self.store.enabled = bool(enabled)

    def reset(self, *, initial_state: str = "idle") -> None:
        self.store = LayerStore()
        self._expire_callbacks.clear()
        self._countdown_invocation_id = None
        self.set_state(initial_state, timestamp=time.monotonic())

    def set_progress(self, value: float, *, color: int = 0x3399FF, background_color: int = 0x03070B) -> None:
        now = time.monotonic()
        self._apply_normalized_commands(
            self.normalizer.normalize_set_progress(
                value,
                color=color,
                background_color=background_color,
                timestamp=now,
            ),
            timestamp=now,
        )

    def set_state_target(
        self,
        target: str,
        config: dict[str, Any] | None = None,
        *,
        slot: str = "primary",
        action: str = "on",
        timestamp: float | None = None,
    ):
        layer_id = self._state_layer(slot)
        resolved = self.effect_registry.resolve_target(target, expected_type=DefinitionType.STATE)
        target_id = self._resolved_target_id(resolved)
        active = self._target_is_active(layer_id, target_id)
        desired = self._resolve_switch_action(action, active)
        if not desired:
            if active:
                self._clear_layer(layer_id)
            return None
        return self._apply_resolved_target(
            resolved,
            layer_id,
            config=config,
            timestamp=timestamp,
            scene_name=f"state:{slot}",
        )

    def clear_state_target(self, *, slot: str = "primary") -> None:
        self._clear_layer(self._state_layer(slot))

    def set_overlay(
        self,
        target: str,
        channel: str | None = None,
        config: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        *,
        action: str = "on",
        timestamp: float | None = None,
    ):
        resolved = self.effect_registry.resolve_target(target, expected_type=DefinitionType.OVERLAY)
        definition = resolved.effect.definition
        if definition.overlay_mode is OverlayMode.CONTROLLED:
            normalized_channel = self._normalize_channel(channel)
        else:
            if action != "on":
                raise ValueError("Timed overlays support only action 'on'")
            normalized_channel = (
                None if channel is None else self._normalize_channel(channel)
            )
        layer_id = (
            LayerId.TEMP_OVERLAY_LAYER
            if definition.overlay_mode is OverlayMode.TIMED
            else LayerId.ONGOING_OVERLAY_LAYER
        )
        if definition.overlay_mode is OverlayMode.CONTROLLED:
            target_id = self._resolved_target_id(resolved)
            active = self._channel_is_active(layer_id, normalized_channel) and self._target_is_active(
                layer_id,
                target_id,
            )
            desired = self._resolve_switch_action(action, active)
            if not desired:
                if active:
                    self._clear_layer(layer_id)
                return None
        return self._apply_resolved_target(
            resolved,
            layer_id,
            config=config,
            inputs=inputs,
            timestamp=timestamp,
            scene_name=(
                f"overlay:{normalized_channel}"
                if normalized_channel is not None
                else f"overlay:{definition.id}"
            ),
            metadata=(
                {} if normalized_channel is None else {"channel": normalized_channel}
            ),
        )

    def update_overlay(
        self,
        channel: str,
        inputs: dict[str, Any],
        *,
        timestamp: float | None = None,
    ) -> EffectInvocation:
        normalized_channel = self._normalize_channel(channel)
        layer_id, invocation = self._find_overlay_channel(normalized_channel)
        registered = self.effect_registry.get(invocation.effect_id)
        definition = registered.definition
        if definition.overlay_mode is not OverlayMode.CONTROLLED:
            raise ValueError(f"Overlay channel {normalized_channel!r} is timed and cannot be updated")
        normalized = normalize_runtime_inputs(definition, inputs)
        invocation.inputs.update(normalized)
        now = _timestamp_or_now(timestamp)
        invocation.input_last_attempt_at = now
        invocation.input_last_success_at = now
        invocation.input_error = None
        return invocation

    def clear_overlay(self, channel: str) -> None:
        normalized_channel = self._normalize_channel(channel)
        layer_id, _ = self._find_overlay_channel(normalized_channel)
        self._clear_layer(layer_id)

    def emit_event_target(
        self,
        target: str,
        config: dict[str, Any] | None = None,
        *,
        priority: int | None = None,
        timestamp: float | None = None,
    ):
        resolved = self.effect_registry.resolve_target(target, expected_type=DefinitionType.EVENT)
        return self._apply_resolved_target(
            resolved,
            LayerId.EVENT_LAYER,
            config=config,
            timestamp=timestamp,
            priority=priority,
            enqueue=True,
            scene_name=f"event:{resolved.effect.local_effect_id}",
        )

    def _apply_resolved_target(
        self,
        resolved,
        layer_id: LayerId,
        *,
        config: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        timestamp: float | None = None,
        priority: int | None = None,
        enqueue: bool = False,
        scene_name: str,
        metadata: dict[str, Any] | None = None,
    ):
        definition = resolved.effect.definition
        normalized_config = resolve_configuration(
            definition,
            preset=resolved.preset_params,
            overrides=config,
        )
        normalized_inputs = normalize_runtime_inputs(definition, inputs)
        duration_ms = None
        if definition.definition_type is DefinitionType.EVENT or (
            definition.definition_type is DefinitionType.OVERLAY
            and definition.overlay_mode is OverlayMode.TIMED
        ):
            raw_duration = normalized_config.get("duration_ms", normalized_config.get("total_ms"))
            if raw_duration is None:
                raise ValueError(
                    f"{definition.definition_type.value.title()} {definition.id!r} "
                    "must define duration_ms or total_ms"
                )
            duration_ms = max(1, int(raw_duration))
        meta = dict(metadata or {})
        meta["target_id"] = self._resolved_target_id(resolved)
        if resolved.preset_id is not None:
            meta["preset_id"] = resolved.preset_id
        for key, value in meta.items():
            normalized_config[f"__{key}"] = value
        return self.apply_effect(
            resolved.effect.registered_id,
            layer_id,
            normalized_config,
            inputs=normalized_inputs,
            duration_ms=duration_ms,
            priority=priority,
            enqueue=enqueue,
            scene_name=scene_name,
            item_id=resolved.preset_id or resolved.effect.qualified_effect_id,
            mode=definition.definition_type.value,
            timestamp=timestamp,
        )

    def _state_layer(self, slot: str) -> LayerId:
        normalized = str(slot or "").strip().lower().replace("-", "_")
        layers = {
            "background": LayerId.BACKGROUND_STATE_LAYER,
            "primary": LayerId.STATE_LAYER,
            "state": LayerId.STATE_LAYER,
        }
        if normalized not in layers:
            raise ValueError("State slot must be 'background' or 'primary'")
        return layers[normalized]

    def _normalize_channel(self, channel: str | None) -> str:
        normalized = str(channel or "").strip().lower().replace("-", "_")
        if not normalized:
            raise ValueError("Overlay channel must not be empty")
        return normalized

    def _resolved_target_id(self, resolved) -> str:
        return resolved.preset_id or resolved.effect.qualified_effect_id

    def _channel_is_active(self, layer_id: LayerId, channel: str) -> bool:
        invocation = self.store.layer(layer_id).state.active_invocation
        return invocation is not None and invocation.params.get("__channel") == channel

    def _find_overlay_channel(self, channel: str) -> tuple[LayerId, EffectInvocation]:
        for layer_id in (LayerId.ONGOING_OVERLAY_LAYER, LayerId.TEMP_OVERLAY_LAYER):
            invocation = self.store.layer(layer_id).state.active_invocation
            if invocation is not None and invocation.params.get("__channel") == channel:
                return layer_id, invocation
        raise KeyError(f"Unknown active overlay channel {channel!r}")

    def _target_is_active(self, layer_id: LayerId, target_id: str) -> bool:
        invocation = self.store.layer(layer_id).state.active_invocation
        if invocation is None:
            return False
        active_target_id = invocation.params.get("__target_id")
        if active_target_id is not None:
            return active_target_id == target_id
        return self.effect_registry.get(invocation.effect_id).qualified_effect_id == target_id

    def _resolve_switch_action(self, action: str, active: bool) -> bool:
        normalized = str(action or "on").strip().lower()
        if normalized == "toggle":
            return not active
        if normalized in {"on", "true", "1"}:
            return True
        if normalized in {"off", "false", "0"}:
            return False
        raise ValueError("Action must be 'on', 'off', or 'toggle'")

    def apply_effect(
        self,
        effect_id: str,
        target_layer: LayerId,
        params: dict[str, Any] | None = None,
        *,
        inputs: dict[str, Any] | None = None,
        duration_ms: int | None = None,
        priority: int | None = None,
        scene_name: str | None = None,
        item_id: str | None = None,
        mode: str | None = None,
        payload: dict[str, Any] | None = None,
        valid: bool = True,
        enqueue: bool = False,
        replace_existing: bool = True,
        timestamp: float | None = None,
    ):
        command_params = canonicalize_effect_params(params)
        if duration_ms is not None:
            command_params["duration_ms"] = int(duration_ms)
        if scene_name is not None:
            command_params["__scene_name"] = scene_name
        if item_id is not None:
            command_params["__item_id"] = item_id
        if mode is not None:
            command_params["__mode"] = mode
        if payload is not None:
            command_params["__payload"] = canonicalize_effect_params(payload)
        command_params["__valid"] = bool(valid)
        now = _timestamp_or_now(timestamp)
        applied = self._apply_normalized_commands(
            [
                NormalizedCommand(
                    kind=CommandKind.SET_EFFECT,
                    target_layer=target_layer,
                    effect_id=effect_id,
                    params=command_params,
                    inputs=dict(inputs or {}),
                    priority=priority,
                    timestamp=now,
                    enqueue=enqueue,
                    replace_existing=replace_existing,
                )
            ],
            timestamp=now,
        )
        return None if not applied else applied[0]

    def clear_layer(self, target_layer: LayerId) -> None:
        self._clear_layer(target_layer)

    def apply_default_background_state(self) -> None:
        self.apply_effect(
            "solid_color",
            LayerId.BACKGROUND_STATE_LAYER,
            {"color": "#FFFFFF", "brightness": 0.2},
            scene_name="state_layer",
            item_id="background-fallback",
            mode="background_fallback",
            payload={"source": "background_state_fallback"},
            timestamp=time.monotonic(),
        )

    def restore_persisted_background_state(self, persisted_state: PersistedLayerState) -> None:
        if persisted_state.layer_id is not LayerId.BACKGROUND_STATE_LAYER:
            raise ValueError("Only BACKGROUND_STATE_LAYER can be restored from persisted state")

        self.apply_effect(
            persisted_state.effect_id,
            LayerId.BACKGROUND_STATE_LAYER,
            self._restore_persisted_value(persisted_state.params),
            scene_name="state_layer",
            item_id="background-restored",
            mode="background_restored",
            payload={"source": "background_state_store"},
            valid=True,
            timestamp=time.monotonic(),
        )

    def background_state_signature(self) -> str | None:
        invocation = self.store.layer(LayerId.BACKGROUND_STATE_LAYER).state.active_invocation
        if invocation is None:
            return None

        entry = self.store.layer(LayerId.BACKGROUND_STATE_LAYER)
        signature = {
            "effect_id": invocation.effect_id,
            "mode": entry.mode,
            "params": self._signature_value(_public_params(invocation.params)),
        }
        return json.dumps(signature, ensure_ascii=True, sort_keys=True)

    def background_state_persistence_snapshot(self) -> tuple[str, PersistedLayerState | None]:
        entry = self.store.layer(LayerId.BACKGROUND_STATE_LAYER)
        invocation = entry.state.active_invocation
        if invocation is None:
            return "empty", None

        if (entry.mode or "") in _NON_PERSISTENT_BACKGROUND_MODES:
            return "skip", None

        rule = self.effect_registry.get(invocation.effect_id).definition.layer_rules.get(LayerId.BACKGROUND_STATE_LAYER)
        if rule is None or not rule.persistent_storage:
            return "skip", None

        try:
            params = self._serialize_persistable_value(_public_params(invocation.params))
        except TypeError:
            return "skip", None

        return (
            "persistable",
            PersistedLayerState(
                schema_version=1,
                layer_id=LayerId.BACKGROUND_STATE_LAYER,
                effect_id=invocation.effect_id,
                params=params,
                enabled=invocation.enabled,
                transparent=invocation.transparent,
                saved_at=time.time(),
            ),
        )

    def render_once(self, now: float | None = None) -> tuple[Scene, Frame]:
        now = time.monotonic() if now is None else now
        self._refresh_automations(now)
        scene = self.composer.compose(self.store, now)
        frame = self.renderer.render(scene)
        frame = self._apply_output_settings(frame)
        self.adapter.apply_frame(frame)
        self.last_scene = scene
        self.last_frame = frame
        return scene, frame

    def run(self, *, seconds: float | None = None, fps: float = 12.0, tick: TickCallback | None = None) -> None:
        interval = 1.0 / max(1.0, fps)
        deadline = None if seconds is None else time.monotonic() + seconds
        while True:
            now = time.monotonic()
            if tick is not None:
                tick(self, now)
            self.render_once(now)
            if deadline is not None and now >= deadline:
                break
            time.sleep(interval)

    def close(self) -> None:
        self.adapter.close()

    def get_status(self, now: float | None = None) -> dict:
        now = time.monotonic() if now is None else now
        current_event = self.store.current_event
        pending_events = self.store.pending_events
        return {
            "base_state": {
                "name": self.store.base_state.name,
                "payload": self._sanitize_value(self.store.base_state.payload),
                "updated_at": self.store.base_state.updated_at,
            },
            "direction": self.store.direction,
            "brightness": self.store.brightness,
            "enabled": self.store.enabled,
            "countdown": None
            if self.store.countdown is None
            else {
                "total_ms": self.store.countdown.total_ms,
                "remaining_ms": self.store.countdown.remaining_at(now),
                "follow_up_state": self.store.countdown.follow_up_state,
                "active": self.store.countdown.active,
                "payload": self._sanitize_value(self.store.countdown.payload),
            },
            "event_overlay": {
                "current": None if current_event is None else self._serialize_event_invocation(current_event),
                "pending": [self._serialize_event_invocation(event) for event in pending_events],
            },
            "render_layers": {
                "background_state_visual": self._serialize_layer_visual(
                    LayerId.BACKGROUND_STATE_LAYER,
                    now,
                ),
                "state_visual": self._serialize_layer_visual(LayerId.STATE_LAYER, now),
                "direction_visual": self._serialize_layer_visual(
                    LayerId.ONGOING_OVERLAY_LAYER,
                    now,
                ),
                "countdown_visual": self._serialize_layer_visual(
                    LayerId.TEMP_OVERLAY_LAYER,
                    now,
                ),
            },
            "last_scene": self._serialize_scene(self.last_scene),
            "last_frame": self._serialize_frame(self.last_frame),
        }

    def _countdown_expire_callback(self, invocation_id: str, follow_up_state: str | None) -> Callable[[float], None]:
        def _callback(expired_at: float) -> None:
            if self._countdown_invocation_id == invocation_id:
                self._countdown_invocation_id = None
            self.store.countdown = None
            if follow_up_state:
                self.set_state(follow_up_state, timestamp=expired_at)

        return _callback

    def _clear_layer(self, layer_id: LayerId) -> None:
        removed_ids = self.store.clear_layer(layer_id)
        for invocation_id in removed_ids:
            self._expire_callbacks.pop(invocation_id, None)

    def _apply_normalized_commands(self, commands: list, *, timestamp: float | None = None):
        now = _timestamp_or_now(timestamp)
        applied = []
        for command in commands:
            if command.kind is CommandKind.CLEAR_LAYER:
                if command.target_layer is not None:
                    self._clear_layer(command.target_layer)
                continue

            created_at = now if command.timestamp is None else float(command.timestamp)
            invocation = build_effect_invocation(
                command,
                self.effect_registry,
                invocation_id=self._next_invocation_id(command),
                created_at=created_at,
            )
            registered = self.effect_registry.get(invocation.effect_id)
            if registered.definition.effective_input_sampling() is not None and invocation.inputs:
                invocation.input_last_attempt_at = created_at
                invocation.input_last_success_at = created_at
            removed_ids = self.store.set_invocation(
                invocation.target_layer,
                invocation,
                scene_name=self._meta_text(invocation.params, "scene_name"),
                item_id=self._meta_text(invocation.params, "item_id") or invocation.invocation_id,
                mode=self._meta_text(invocation.params, "mode"),
                payload=self._meta_payload(invocation.params),
                valid=self._meta_bool(invocation.params, "valid", True),
                enqueue=command.enqueue,
            )
            for invocation_id in removed_ids:
                self._expire_callbacks.pop(invocation_id, None)
            applied.append(invocation)

        return applied

    def _next_invocation_id(self, command) -> str:
        explicit = command.params.get("__invocation_id")
        if explicit:
            return str(explicit)
        self._invocation_sequence += 1
        base = command.effect_id or command.kind.value
        return f"{base}:{self._invocation_sequence}"

    def _meta_text(self, params: dict[str, Any], name: str) -> str | None:
        value = params.get(f"__{name}")
        if value is None:
            return None
        return str(value)

    def _meta_payload(self, params: dict[str, Any]) -> dict[str, Any]:
        payload = params.get("__payload")
        return dict(payload) if isinstance(payload, dict) else {}

    def _meta_bool(self, params: dict[str, Any], name: str, default: bool) -> bool:
        value = params.get(f"__{name}")
        return default if value is None else bool(value)

    def _refresh_automations(self, now: float) -> None:
        expired_ids = self.store.advance(now)
        for invocation_id in expired_ids:
            callback = self._expire_callbacks.pop(invocation_id, None)
            if callback is not None:
                callback(now)
            elif invocation_id == self._countdown_invocation_id:
                self._countdown_invocation_id = None
                self.store.countdown = None

    def _apply_output_settings(self, frame: Frame) -> Frame:
        leds = list(frame.leds)
        if not self.store.enabled:
            leds = [0] * len(leds)
        elif self.store.brightness < 1.0:
            from ..core.color_math import scale_color

            leds = [scale_color(color, self.store.brightness) for color in leds]
        return Frame(leds=leds, timestamp=frame.timestamp)

    def _sanitize_value(self, value):
        if callable(value):
            return "<callable>"
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {str(key): self._sanitize_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._sanitize_value(item) for item in value]
        return value

    def _serialize_persistable_value(self, value):
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, Path):
            return str(value)
        if callable(value):
            raise TypeError("Callables cannot be persisted")
        if isinstance(value, dict):
            return {str(key): self._serialize_persistable_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._serialize_persistable_value(item) for item in value]
        raise TypeError(f"Unsupported persisted value: {value!r}")

    def _restore_persisted_value(self, value):
        if isinstance(value, dict):
            return {str(key): self._restore_persisted_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._restore_persisted_value(item) for item in value]
        return value

    def _signature_value(self, value):
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, Path):
            return str(value)
        if callable(value):
            return "<callable>"
        if isinstance(value, dict):
            return {str(key): self._signature_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._signature_value(item) for item in value]
        return repr(value)

    def _serialize_invocation_visual(self, invocation, now: float) -> dict:
        registered = self.effect_registry.get(invocation.effect_id)
        return {
            "effect_id": invocation.effect_id,
            "playback_mode": None if invocation.playback_mode is None else invocation.playback_mode.value,
            "requested_duration_ms": invocation.requested_duration_ms,
            "params": self._sanitize_value(_public_params(invocation.params)),
            "inputs": self._sanitize_value(invocation.inputs),
            "input_health": self._serialize_input_health(
                registered.definition,
                invocation,
                now,
            ),
        }

    def _serialize_input_health(self, definition, invocation, now: float) -> dict | None:
        policy = definition.effective_input_sampling()
        if policy is None:
            return None
        anchor = (
            invocation.created_at
            if invocation.input_last_success_at is None
            else invocation.input_last_success_at
        )
        age_ms = max(0, int(round((now - anchor) * 1000.0)))
        missed = min(
            policy.max_missed_heartbeats,
            age_ms // policy.heartbeat_interval_ms,
        )
        if age_ms >= policy.failure_after_ms:
            status = "failed"
        elif invocation.input_last_success_at is None:
            status = "waiting"
        else:
            status = "healthy"
        return {
            "mode": policy.mode.value,
            "status": status,
            "age_ms": age_ms,
            "missed_heartbeats": missed,
            "max_missed_heartbeats": policy.max_missed_heartbeats,
            "last_error": invocation.input_error,
        }

    def _serialize_layer_visual(self, layer_id: LayerId, now: float) -> dict | None:
        invocation = self.store.layer(layer_id).state.active_invocation
        if invocation is None:
            return None
        return self._serialize_invocation_visual(invocation, now)

    def _serialize_event_invocation(self, invocation) -> dict:
        return {
            "id": self._meta_text(invocation.params, "item_id") or invocation.invocation_id,
            "name": self._meta_text(invocation.params, "event_name") or invocation.effect_id,
            "priority": invocation.effective_priority(),
            "created_at": invocation.created_at,
            "duration": None if invocation.requested_duration_ms is None else invocation.requested_duration_ms / 1000.0,
            "exclusive": False,
            "payload": self._sanitize_value(self._meta_payload(invocation.params)),
        }

    def _serialize_scene(self, scene: Scene | None) -> dict | None:
        if scene is None:
            return None
        return {
            "timestamp": scene.timestamp,
            "diagnostics": list(scene.diagnostics),
            "main_layer_valid": scene.main_layer_valid,
            "layers": [
                {
                    "name": layer.name,
                    "priority": layer.priority,
                    "visual": {
                        "type": layer.visual.type,
                        "exclusive": layer.visual.exclusive,
                        "params": self._sanitize_value(layer.visual.params),
                    },
                }
                for layer in scene.layers
            ],
        }

    def _serialize_frame(self, frame: Frame | None) -> dict | None:
        if frame is None:
            return None
        return {"timestamp": frame.timestamp, "leds": list(frame.leds)}


LedController = ControllerRuntime
