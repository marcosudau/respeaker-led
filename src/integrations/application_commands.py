from __future__ import annotations

from typing import Any

from ..engine.effect_registry import EffectRegistry
from ..core.effect_schema import CommandKind, EffectInvocation, LayerId, NormalizedCommand, PlaybackMode
from ..infrastructure.spec_utils import parse_hex_color


DEFAULT_EVENT_PRIORITIES = {
    "error_flash": 900,
    "timeout_imminent": 800,
    "wakeword_ack": 725,
    "trigger_received": 700,
    "warning": 600,
    "text_committed": 500,
    "notification": 400,
}
DEFAULT_EVENT_DURATIONS_MS = {
    "error_flash": 1800,
    "timeout_imminent": 1500,
    "wakeword_ack": 900,
    "trigger_received": 900,
    "warning": 1400,
    "text_committed": 1200,
    "notification": 1000,
}

_PUBLIC_EFFECT_PARAM_ALIASES = {
    "base_color": "background_color",
    "color_a": "color",
    "color_b": "secondary_color",
    "direction": "direction_deg",
    "fill_level": "progress",
    "marker_color": "secondary_color",
    "progress_value": "progress",
    "value": "progress",
}


def _normalize_name(value: str, fallback: str) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    return text or fallback


def _copy_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    return dict(payload or {})


def canonicalize_effect_params(params: dict[str, Any] | None) -> dict[str, Any]:
    canonical: dict[str, Any] = {}
    for key, value in dict(params or {}).items():
        name = str(key)
        if name.startswith("__"):
            canonical[name] = value
            continue
        normalized = _PUBLIC_EFFECT_PARAM_ALIASES.get(name, name)
        if normalized not in canonical or normalized == name:
            canonical[normalized] = value
    return canonical


def _meta(params: dict[str, Any], **metadata: Any) -> dict[str, Any]:
    enriched = dict(params)
    for key, value in metadata.items():
        if value is not None:
            enriched[f"__{key}"] = value
    return enriched


def _default_state_color(state_name: str) -> int:
    return {
        "offline": 0x6A0F0F,
        "idle": 0x10263D,
        "listening": 0x1AA7FF,
        "recording": 0x19D37A,
        "transcribing": 0xFFB347,
        "processing": 0xFFB347,
        "error": 0xFF3B30,
    }.get(state_name, 0x7AA4FF)


def _default_background_color(state_name: str) -> int:
    return {
        "offline": 0x080101,
        "idle": 0x010408,
        "listening": 0x020810,
        "recording": 0x031108,
        "transcribing": 0x120A02,
        "processing": 0x120A02,
        "error": 0x120103,
    }.get(state_name, 0x060812)


def _default_event_color(event_name: str) -> int:
    return {
        "trigger_received": 0x33D1FF,
        "wakeword_ack": 0x33D1FF,
        "text_committed": 0x42D392,
        "warning": 0xFFB347,
        "error_flash": 0xFF3B30,
        "timeout_imminent": 0xFF9F1A,
    }.get(event_name, 0x7AA4FF)


def _default_event_background(event_name: str) -> int:
    return {
        "trigger_received": 0x05131A,
        "wakeword_ack": 0x05131A,
        "text_committed": 0x06120B,
        "warning": 0x1A1005,
        "error_flash": 0x120103,
        "timeout_imminent": 0x190D02,
    }.get(event_name, 0x05070A)


def _payload_period_ms(payload: dict[str, Any], default_ms: int) -> int:
    if "period_ms" in payload:
        return max(100, int(payload["period_ms"]))
    if "period" in payload:
        return max(100, int(float(payload["period"]) * 1000.0))
    return default_ms


def _payload_speed(
    payload: dict[str, Any],
    *,
    base_period_ms: int,
    default_period_ms: int,
) -> float:
    if "speed" in payload:
        return max(0.1, min(10.0, float(payload["speed"])))
    period_ms = _payload_period_ms(payload, default_period_ms)
    return max(0.1, min(10.0, base_period_ms / float(period_ms)))


def _payload_color(payload: dict[str, Any], key: str, default: int, *aliases: str) -> int:
    for candidate in (key, *aliases):
        if candidate in payload:
            return parse_hex_color(payload.get(candidate), default)
    return default


class ControllerCommandNormalizer:
    def normalize_set_state(
        self,
        state_name: str,
        payload: dict[str, Any] | None = None,
        *,
        source: str = "runtime.set_state",
        timestamp: float | None = None,
    ) -> list[NormalizedCommand]:
        name = _normalize_name(state_name, "idle")
        payload = _copy_payload(payload)
        accent = parse_hex_color(payload.get("color"), _default_state_color(name))
        background = _payload_color(payload, "background_color", _default_background_color(name), "base_color")
        commands = [
            NormalizedCommand(
                kind=CommandKind.SET_EFFECT,
                target_layer=LayerId.BACKGROUND_STATE_LAYER,
                effect_id="solid_color",
                params=_meta(
                    {"color": background},
                    scene_name="state_layer",
                    item_id=name,
                    mode=name,
                    payload=payload,
                    valid=True,
                ),
                source=source,
                timestamp=timestamp,
            )
        ]

        if name == "idle":
            commands.append(
                NormalizedCommand(
                    kind=CommandKind.CLEAR_LAYER,
                    target_layer=LayerId.STATE_LAYER,
                    source=source,
                    timestamp=timestamp,
                )
            )
            return commands

        effect_id = "soft_pulse"
        effect_params: dict[str, Any] = {
            "color": accent,
            "background_color": background,
            "speed": _payload_speed(
                payload,
                base_period_ms=1800,
                default_period_ms=1600,
            ),
        }
        if name == "offline":
            effect_id = "blink_color"
            effect_params = {
                "color": accent,
                "background_color": background,
                "speed": 900 / 1200,
                "duty_cycle": 0.25,
            }
        elif name == "listening":
            effect_params["speed"] = 1.0
        elif name == "recording":
            effect_params["speed"] = 1800 / 1100
        elif name in {"transcribing", "processing"}:
            effect_params["speed"] = 1800 / 1400
        elif name == "error":
            effect_id = "blink_color"
            effect_params = {
                "color": accent,
                "background_color": background,
                "speed": 900 / 700,
                "duty_cycle": 0.55,
            }

        commands.append(
            NormalizedCommand(
                kind=CommandKind.SET_EFFECT,
                target_layer=LayerId.STATE_LAYER,
                effect_id=effect_id,
                params=_meta(
                    effect_params,
                    scene_name=f"state:primary:{name}",
                    item_id=f"base-state:{name}",
                    mode=name,
                    payload=payload,
                    valid=True,
                ),
                source=source,
                timestamp=timestamp,
            )
        )
        return commands

    def normalize_clear_state(
        self,
        state_name: str | None = None,
        *,
        source: str = "runtime.clear_state",
        timestamp: float | None = None,
    ) -> list[NormalizedCommand]:
        return self.normalize_set_state(state_name or "idle", source=source, timestamp=timestamp)

    def normalize_emit_event(
        self,
        event_name: str,
        payload: dict[str, Any] | None = None,
        *,
        source: str = "runtime.emit_event",
        timestamp: float | None = None,
    ) -> list[NormalizedCommand]:
        name = _normalize_name(event_name, "notification")
        payload = _copy_payload(payload)
        effect_id = (
            "warning_flash"
            if name in {"warning", "error_flash", "timeout_imminent"}
            else "short_flash"
        )
        event_id = str(payload.get("event_id", f"{name}-{int((timestamp or 0.0) * 1000)}"))
        duration_ms = payload.get("duration_ms", DEFAULT_EVENT_DURATIONS_MS.get(name, 1000))
        priority = int(payload.get("priority", DEFAULT_EVENT_PRIORITIES.get(name, 300)))
        accent = parse_hex_color(payload.get("color"), _default_event_color(name))
        background = _payload_color(payload, "background_color", _default_event_background(name), "base_color")
        params = {
            "color": accent,
            "background_color": background,
            "duration_ms": None if duration_ms is None else int(duration_ms),
        }
        if effect_id == "warning_flash":
            period_ms, duty_cycle = {
                "error_flash": (350, 0.6),
                "timeout_imminent": (400, 0.5),
                "warning": (800, 0.5),
            }.get(name, (900, 0.45))
            params.update(
                {
                    "speed": 400 / float(period_ms),
                    "duty_cycle": duty_cycle,
                }
            )
        return [
            NormalizedCommand(
                kind=CommandKind.SET_EFFECT,
                target_layer=LayerId.EVENT_LAYER,
                effect_id=effect_id,
                params=_meta(
                    params,
                    scene_name=f"event:{event_id}",
                    item_id=event_id,
                    event_name=name,
                    payload=payload,
                    valid=True,
                    invocation_id=event_id,
                ),
                priority=priority,
                source=source,
                timestamp=timestamp,
                enqueue=True,
                replace_existing=False,
            )
        ]

    def normalize_set_direction(
        self,
        direction: float,
        *,
        source: str = "runtime.set_direction",
        timestamp: float | None = None,
    ) -> list[NormalizedCommand]:
        normalized = float(direction) % 360.0
        return [
            NormalizedCommand(
                kind=CommandKind.SET_EFFECT,
                target_layer=LayerId.ONGOING_OVERLAY_LAYER,
                effect_id="direction_indicator",
                params=_meta(
                    {},
                    scene_name="direction_overlay",
                    item_id="direction-overlay",
                    mode="direction",
                    payload={
                        "direction_deg": normalized,
                        "detection_state": "sound",
                    },
                    valid=True,
                ),
                inputs={
                    "direction_deg": normalized,
                    "detection_state": "sound",
                },
                source=source,
                timestamp=timestamp,
            )
        ]

    def normalize_clear_direction(
        self,
        *,
        source: str = "runtime.clear_direction",
        timestamp: float | None = None,
    ) -> list[NormalizedCommand]:
        return [
            NormalizedCommand(
                kind=CommandKind.CLEAR_LAYER,
                target_layer=LayerId.ONGOING_OVERLAY_LAYER,
                source=source,
                timestamp=timestamp,
            )
        ]

    def normalize_start_timeout_countdown(
        self,
        total_ms: int,
        remaining_ms: int | None = None,
        *,
        follow_up_state: str | None = None,
        payload: dict[str, Any] | None = None,
        source: str = "runtime.start_timeout_countdown",
        timestamp: float | None = None,
    ) -> list[NormalizedCommand]:
        total_ms = max(1, int(total_ms))
        remaining_ms = total_ms if remaining_ms is None else max(0, min(int(remaining_ms), total_ms))
        payload = _copy_payload(payload)
        now = 0.0 if timestamp is None else float(timestamp)
        return [
            NormalizedCommand(
                kind=CommandKind.SET_EFFECT,
                target_layer=LayerId.TEMP_OVERLAY_LAYER,
                effect_id="countdown_ring",
                params=_meta(
                    {
                        "total_ms": total_ms,
                        "deadline_ts": now + (remaining_ms / 1000.0),
                        "duration_ms": remaining_ms,
                        "color": parse_hex_color(payload.get("color"), 0xFF9F1A),
                        "secondary_color": parse_hex_color(
                            payload.get("secondary_color", payload.get("marker_color")),
                            0xFFF3D1,
                        ),
                    },
                    scene_name="countdown_overlay",
                    item_id="countdown-overlay",
                    mode="countdown",
                    payload=payload,
                    valid=True,
                    follow_up_state=None if follow_up_state is None else _normalize_name(follow_up_state, ""),
                ),
                source=source,
                timestamp=timestamp,
            )
        ]

    def normalize_cancel_timeout_countdown(
        self,
        *,
        source: str = "runtime.cancel_timeout_countdown",
        timestamp: float | None = None,
    ) -> list[NormalizedCommand]:
        return [
            NormalizedCommand(
                kind=CommandKind.CLEAR_LAYER,
                target_layer=LayerId.TEMP_OVERLAY_LAYER,
                source=source,
                timestamp=timestamp,
            )
        ]

    def normalize_set_progress(
        self,
        value: float,
        *,
        color: int = 0x3399FF,
        background_color: int = 0x03070B,
        source: str = "runtime.set_progress",
        timestamp: float | None = None,
    ) -> list[NormalizedCommand]:
        commands = self.normalize_set_state(
            "transcribing",
            payload={"source": "progress"},
            source=source,
            timestamp=timestamp,
        )
        commands.append(
            NormalizedCommand(
                kind=CommandKind.SET_EFFECT,
                target_layer=LayerId.ONGOING_OVERLAY_LAYER,
                effect_id="progress_bar",
                params=_meta(
                    {"color": int(color), "background_color": int(background_color)},
                    scene_name="overlay:progress",
                    item_id="progress",
                    mode="progress",
                    payload={"progress": float(value)},
                    valid=True,
                ),
                inputs={"progress": float(value)},
                source=source,
                timestamp=timestamp,
            )
        )
        return commands


def _preferred_playback_mode(layer_id: LayerId, allowed_modes: tuple[PlaybackMode, ...], requested_duration_ms: int | None) -> PlaybackMode:
    candidates = allowed_modes or (PlaybackMode.SINGLE_RUN,)
    if requested_duration_ms is not None and PlaybackMode.SINGLE_RUN in candidates:
        return PlaybackMode.SINGLE_RUN
    preferred = {
        LayerId.BACKGROUND_STATE_LAYER: PlaybackMode.PERSISTENT,
        LayerId.STATE_LAYER: PlaybackMode.PERSISTENT,
        LayerId.TEMP_OVERLAY_LAYER: PlaybackMode.SINGLE_RUN,
        LayerId.ONGOING_OVERLAY_LAYER: PlaybackMode.PERSISTENT,
        LayerId.EVENT_LAYER: PlaybackMode.SINGLE_RUN,
    }[layer_id]
    if preferred in candidates:
        return preferred
    if layer_id in {LayerId.BACKGROUND_STATE_LAYER, LayerId.STATE_LAYER, LayerId.ONGOING_OVERLAY_LAYER} and PlaybackMode.LOOP in candidates:
        return PlaybackMode.LOOP
    return candidates[0]


def build_effect_invocation(
    command: NormalizedCommand,
    registry: EffectRegistry,
    *,
    invocation_id: str,
    created_at: float,
) -> EffectInvocation:
    if command.kind is not CommandKind.SET_EFFECT:
        raise ValueError(f"Cannot build invocation from command kind: {command.kind}")
    if command.target_layer is None:
        raise ValueError("SET_EFFECT command requires a target layer")
    if not command.effect_id:
        raise ValueError("SET_EFFECT command requires an effect_id")

    definition = registry.get(command.effect_id).definition
    rule = definition.layer_rules.get(command.target_layer)
    if rule is None or not rule.allowed:
        raise ValueError(f"Effect {command.effect_id!r} is not allowed on layer {command.target_layer.value}")

    params = dict(command.params)
    requested_duration_ms = params.get("duration_ms")
    if requested_duration_ms is not None:
        requested_duration_ms = max(0, int(requested_duration_ms))

    if rule.requires_finite_duration and requested_duration_ms is None:
        raise ValueError(f"Effect {command.effect_id!r} on {command.target_layer.value} requires a finite duration")
    if rule.requires_indefinite_duration and requested_duration_ms is not None:
        raise ValueError(f"Effect {command.effect_id!r} on {command.target_layer.value} requires an indefinite duration")

    allowed_modes = rule.allowed_playback_modes or definition.capabilities.playback_modes
    playback_mode = _preferred_playback_mode(command.target_layer, allowed_modes, requested_duration_ms)
    return EffectInvocation(
        invocation_id=invocation_id,
        effect_id=command.effect_id,
        target_layer=command.target_layer,
        params=params,
        inputs=dict(command.inputs),
        priority=command.priority,
        playback_mode=playback_mode,
        requested_duration_ms=requested_duration_ms,
        source=command.source,
        created_at=created_at,
        replace_existing=command.replace_existing,
    )


__all__ = [
    "ControllerCommandNormalizer",
    "canonicalize_effect_params",
    "build_effect_invocation",
]
