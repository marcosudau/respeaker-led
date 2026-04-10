from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from ..integrations.adapters import ConsolePreviewAdapter, FrameAdapter
from .composer import SceneComposer
from .effect_registry import EffectRegistry, build_default_effect_registry
from ..core.effect_schema import CommandKind, LayerId, NormalizedCommand, PersistedLayerState
from .effects2 import visual_from_spec
from ..core.layers import LayerStore
from ..core.models import BaseState, CountdownState, Event, Frame, MainLayerState, Scene, StateLayerState, Visual
from .normalization import ControllerCommandNormalizer, build_effect_invocation
from .preset_loader import PresetRegistry
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
        preset_registry: PresetRegistry | None = None,
        effect_registry: EffectRegistry | None = None,
    ) -> None:
        self.effect_registry = effect_registry or build_default_effect_registry()
        self.normalizer = ControllerCommandNormalizer()
        self.store = LayerStore()
        self.composer = SceneComposer(self.effect_registry)
        self.renderer = SceneRenderer()
        self.adapter = adapter or ConsolePreviewAdapter()
        self.presets = preset_registry or PresetRegistry.empty()
        self.last_scene: Scene | None = None
        self.last_frame: Frame | None = None
        self.active_preset_id: str | None = None
        self._expire_callbacks: dict[str, Callable[[float], None]] = {}
        self._invocation_sequence = 0
        self._countdown_invocation_id: str | None = None
        self.reset(initial_state="idle")

    def set_state_layer(self, state_layer: StateLayerState) -> None:
        if not state_layer.enabled or state_layer.visual is None:
            self._clear_layer(LayerId.BACKGROUND_STATE_LAYER)
            return
        now = time.monotonic()
        self._apply_normalized_commands(
            self.normalizer.normalize_legacy_visual(
                LayerId.BACKGROUND_STATE_LAYER,
                state_layer.visual,
                scene_name="state_layer",
                item_id=state_layer.mode,
                mode=state_layer.mode,
                payload={},
                valid=True,
                timestamp=now,
            ),
            timestamp=now,
        )

    def set_state_visual(self, visual, *, mode: str = "custom", enabled: bool = True) -> None:
        if not enabled or visual is None:
            self._clear_layer(LayerId.BACKGROUND_STATE_LAYER)
            return
        now = time.monotonic()
        self._apply_normalized_commands(
            self.normalizer.normalize_legacy_visual(
                LayerId.BACKGROUND_STATE_LAYER,
                visual,
                scene_name="state_layer",
                item_id=mode,
                mode=mode,
                payload={},
                valid=True,
                timestamp=now,
            ),
            timestamp=now,
        )

    def clear_state_layer(self) -> None:
        self._clear_layer(LayerId.BACKGROUND_STATE_LAYER)

    def set_main_layer(self, main_layer: MainLayerState | None) -> None:
        if main_layer is None or main_layer.visual is None:
            self.clear_active_visual()
            return
        self.set_active_visual(
            layer_id=main_layer.id,
            mode=main_layer.mode,
            visual=main_layer.visual,
            payload=main_layer.payload,
            valid=main_layer.valid,
            updated_at=main_layer.updated_at,
        )

    def set_active_visual(
        self,
        *,
        layer_id: str,
        mode: str,
        visual,
        payload: dict | None = None,
        valid: bool = True,
        updated_at: float | None = None,
    ) -> None:
        now = _timestamp_or_now(updated_at)
        self._apply_normalized_commands(
            self.normalizer.normalize_legacy_visual(
                LayerId.MAIN_LAYER,
                visual,
                scene_name=f"active_visual:{layer_id}",
                item_id=layer_id,
                mode=mode,
                payload=_copy_payload(payload),
                valid=valid,
                timestamp=now,
            ),
            timestamp=now,
        )

    def set_main_visual(
        self,
        *,
        layer_id: str,
        mode: str,
        visual,
        payload: dict | None = None,
        valid: bool = True,
        updated_at: float | None = None,
    ) -> None:
        self.set_active_visual(
            layer_id=layer_id,
            mode=mode,
            visual=visual,
            payload=payload,
            valid=valid,
            updated_at=updated_at,
        )

    def clear_active_visual(self) -> None:
        self._clear_layer(LayerId.MAIN_LAYER)
        self.active_preset_id = None

    def clear_main_layer(self) -> None:
        self.clear_active_visual()

    def set_state(self, state_name: str, payload: dict | None = None, *, timestamp: float | None = None) -> None:
        now = _timestamp_or_now(timestamp)
        name = _normalize_name(state_name, "idle")
        copied_payload = _copy_payload(payload)
        self.active_preset_id = None
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

    def set_direction(self, direction_deg: float) -> None:
        normalized = float(direction_deg) % 360.0
        self.store.direction_deg = normalized
        now = time.monotonic()
        self._apply_normalized_commands(
            self.normalizer.normalize_set_direction(normalized, timestamp=now),
            timestamp=now,
        )

    def clear_direction(self) -> None:
        self.store.direction_deg = None
        self._clear_layer(LayerId.ONGOING_OVERLAY_LAYER)

    def set_brightness(self, level: float) -> None:
        self.store.brightness = max(0.0, min(1.0, float(level)))

    def set_enabled(self, enabled: bool) -> None:
        self.store.enabled = bool(enabled)

    def reset(self, *, initial_state: str = "idle") -> None:
        self.store = LayerStore()
        self.active_preset_id = None
        self._expire_callbacks.clear()
        self._countdown_invocation_id = None
        self.set_state(initial_state, timestamp=time.monotonic())

    def apply_preset(self, preset_id: str, spec: dict) -> None:
        preset = self.presets.get_by_id(preset_id)
        result = preset.build_preset(spec)
        self.active_preset_id = result.preset_id
        if result.state_visual is not None:
            self.set_state_visual(result.state_visual, mode=result.state_mode)
        if result.visual is not None:
            self.set_active_visual(
                layer_id=result.preset_id,
                mode=result.mode,
                visual=result.visual,
                payload=result.payload,
                valid=result.valid,
            )

    def apply_preset_from_file(self, preset_id: str, spec_file: str | Path) -> None:
        spec = json.loads(Path(spec_file).read_text(encoding="utf-8"))
        self.apply_preset(preset_id, spec)

    def set_progress(self, value: float, *, color: int = 0x3399FF, base_color: int = 0x03070B) -> None:
        self.active_preset_id = None
        now = time.monotonic()
        self._apply_normalized_commands(
            self.normalizer.normalize_set_progress(value, color=color, base_color=base_color, timestamp=now),
            timestamp=now,
        )

    def push_event(self, event: Event) -> None:
        payload = dict(event.payload)
        payload.setdefault("event_id", event.id)
        payload.setdefault("priority", event.priority)
        if event.duration is not None:
            payload.setdefault("duration_ms", int(event.duration * 1000.0))
        self._apply_normalized_commands(
            self.normalizer.normalize_legacy_visual(
                LayerId.EVENT_LAYER,
                event.visual,
                scene_name=f"event:{event.id}",
                item_id=event.id,
                mode=event.name,
                payload=payload,
                valid=True,
                source="runtime.push_event",
                timestamp=event.created_at,
                priority=event.priority,
                duration_ms=None if event.duration is None else int(event.duration * 1000.0),
                enqueue=True,
                replace_existing=False,
            ),
            timestamp=event.created_at,
        )

    def push_event_visual(
        self,
        *,
        event_id: str,
        kind: str,
        visual,
        priority: int = 100,
        duration: float | None = 3.0,
        exclusive: bool | None = None,
        created_at: float | None = None,
    ) -> None:
        del exclusive
        created_at = time.monotonic() if created_at is None else created_at
        self._apply_normalized_commands(
            self.normalizer.normalize_legacy_visual(
                LayerId.EVENT_LAYER,
                visual,
                scene_name=f"event:{event_id}",
                item_id=event_id,
                mode=kind,
                payload={},
                valid=True,
                source="runtime.push_event_visual",
                timestamp=created_at,
                priority=priority,
                duration_ms=None if duration is None else int(duration * 1000.0),
                enqueue=True,
                replace_existing=False,
            ),
            timestamp=created_at,
        )

    def clear_event_layer(self) -> None:
        self._clear_layer(LayerId.EVENT_LAYER)

    def apply_effect(
        self,
        effect_id: str,
        target_layer: LayerId,
        params: dict[str, Any] | None = None,
        *,
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
        command_params = dict(params or {})
        if duration_ms is not None:
            command_params["duration_ms"] = int(duration_ms)
        if scene_name is not None:
            command_params["__scene_name"] = scene_name
        if item_id is not None:
            command_params["__item_id"] = item_id
        if mode is not None:
            command_params["__mode"] = mode
        if payload is not None:
            command_params["__payload"] = dict(payload)
        command_params["__valid"] = bool(valid)
        now = _timestamp_or_now(timestamp)
        applied = self._apply_normalized_commands(
            [
                NormalizedCommand(
                    kind=CommandKind.SET_EFFECT,
                    target_layer=target_layer,
                    effect_id=effect_id,
                    params=command_params,
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
        main_entry = self.store.layer(LayerId.MAIN_LAYER)
        main_invocation = main_entry.state.active_invocation
        current_event = self.store.current_event
        pending_events = self.store.pending_events
        return {
            "base_state": {
                "name": self.store.base_state.name,
                "payload": self._sanitize_value(self.store.base_state.payload),
                "updated_at": self.store.base_state.updated_at,
            },
            "active_visual": None
            if main_invocation is None
            else {
                "id": main_entry.item_id or main_invocation.invocation_id,
                "mode": main_entry.mode or main_invocation.effect_id,
                "payload": self._sanitize_value(main_entry.payload),
                "updated_at": main_invocation.created_at,
                "valid": main_entry.valid,
                "visual": self._serialize_invocation_visual(main_invocation),
            },
            "active_preset_id": self.active_preset_id,
            "direction_deg": self.store.direction_deg,
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
                "state_visual": self._serialize_layer_visual(LayerId.BACKGROUND_STATE_LAYER),
                "direction_visual": self._serialize_layer_visual(LayerId.ONGOING_OVERLAY_LAYER),
                "countdown_visual": self._serialize_layer_visual(LayerId.TEMP_OVERLAY_LAYER),
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
        if isinstance(value, Visual):
            return {
                "__type__": "visual_spec",
                "type": value.type,
                "params": self._serialize_persistable_value(value.params),
                "exclusive": bool(value.exclusive),
            }
        if callable(value):
            raise TypeError("Callables cannot be persisted")
        if isinstance(value, dict):
            return {str(key): self._serialize_persistable_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._serialize_persistable_value(item) for item in value]
        raise TypeError(f"Unsupported persisted value: {value!r}")

    def _restore_persisted_value(self, value):
        if isinstance(value, dict):
            if value.get("__type__") == "visual_spec":
                spec = {
                    "type": value.get("type"),
                    "params": self._restore_persisted_value(value.get("params", {})),
                    "exclusive": bool(value.get("exclusive", False)),
                }
                return visual_from_spec(spec)
            return {str(key): self._restore_persisted_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._restore_persisted_value(item) for item in value]
        return value

    def _signature_value(self, value):
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, Visual):
            return {
                "__type__": "visual_spec",
                "type": value.type,
                "params": self._signature_value(value.params),
                "exclusive": bool(value.exclusive),
            }
        if callable(value):
            return "<callable>"
        if isinstance(value, dict):
            return {str(key): self._signature_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._signature_value(item) for item in value]
        return repr(value)

    def _serialize_invocation_visual(self, invocation) -> dict:
        return {
            "effect_id": invocation.effect_id,
            "playback_mode": None if invocation.playback_mode is None else invocation.playback_mode.value,
            "requested_duration_ms": invocation.requested_duration_ms,
            "params": self._sanitize_value(_public_params(invocation.params)),
        }

    def _serialize_layer_visual(self, layer_id: LayerId) -> dict | None:
        invocation = self.store.layer(layer_id).state.active_invocation
        if invocation is None:
            return None
        return self._serialize_invocation_visual(invocation)

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