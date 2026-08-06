from __future__ import annotations

import hashlib
import math
from typing import Any

from respeaker_led.core.color_math import blend, scale_color
from respeaker_led.core.effect_schema import (
    BaseEffect,
    ColorModel,
    CompositionMode,
    InputSamplingPolicy,
    DefinitionType,
    EffectCapabilities,
    EffectDefinition,
    EffectParamDefinition,
    LayerId,
    LayerRule,
    OverlayMode,
    PlaybackMode,
    QueueMode,
    RenderContext,
)


def _merge_params(ctx: RenderContext) -> dict[str, Any]:
    params = dict(ctx.definition.defaults)
    params.update(ctx.params)
    params.update(ctx.inputs)
    return params


def _parse_color(value: Any, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value

    text = str(value).strip()
    if not text:
        return default
    if text.startswith("#"):
        return int(text[1:], 16)
    if text.lower().startswith("0x"):
        return int(text, 16)
    return int(text, 16)


def _parse_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _event_rules() -> dict[LayerId, LayerRule]:
    return {
        LayerId.EVENT_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
            requires_finite_duration=True,
            queue_mode=QueueMode.PRIORITY_FIFO,
        )
    }


def _brightness_param() -> EffectParamDefinition:
    return EffectParamDefinition(name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0)


def _reverse_param() -> EffectParamDefinition:
    return EffectParamDefinition(name="reverse", type="bool", default=False)


def _raw_color_param(
    params: dict[str, Any],
    key: str,
    default: int,
    *aliases: str,
) -> int:
    for candidate in (key, *aliases):
        if candidate in params:
            return _parse_color(params.get(candidate), default)
    return default


def _background_color(params: dict[str, Any], default: int = 0x000000) -> int:
    return _raw_color_param(params, "background_color", default, "base_color")


def _parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _step_sign(params: dict[str, Any], default_reverse: bool = False) -> int:
    return -1 if _parse_bool(params.get("reverse"), default_reverse) else 1


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _wrap_index(index: int, led_count: int) -> int:
    return index % max(1, led_count)


def _decay_factor(index: int, length: int, curve: str) -> float:
    if length <= 1:
        return 1.0
    normalized = 1.0 - (index / float(length - 1))
    if curve == "quadratic":
        return normalized * normalized
    if curve == "exponential":
        return normalized**3
    return normalized


def _event_duration_ms(ctx: RenderContext, params: dict[str, Any], default_ms: int) -> int:
    requested = ctx.invocation.requested_duration_ms
    if requested is None:
        requested = _parse_int(params.get("duration_ms"), default_ms)
    return max(1, int(requested))


def _elapsed_fraction(ctx: RenderContext, params: dict[str, Any], default_ms: int) -> float:
    duration_ms = _event_duration_ms(ctx, params, default_ms)
    elapsed_ms = max(0.0, (ctx.now - ctx.invocation.created_at) * 1000.0)
    return _clamp01(elapsed_ms / float(duration_ms))


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="short_ping",
        definition_type=DefinitionType.EVENT,
        title="Short Ping",
        description="Kurzer Ping mit Start-LED, Richtung und auslaufendem Schweif.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "start_led": EffectParamDefinition(name="start_led", type="int", default=0, minimum=0),
            "reverse": _reverse_param(),
            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=700, minimum=1, unit="ms"),
        },
        defaults={
            "color": "#33AAFF",
            "background_color": "#000000",
            "brightness": 1.0,
            "start_led": 0,
            "reverse": False,
            "duration_ms": 700,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
        ),
        layer_rules=_event_rules(),
        color_model=ColorModel.MONO,
        composition=CompositionMode.OPAQUE,
        animated=False,
        directional=True,
        tags=("builtin", "event", "ping"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame = [_background_color(params)] * ctx.led_count
        phase = _elapsed_fraction(ctx, params, 700)
        step_sign = _step_sign(params)
        start_led = _wrap_index(_parse_int(params.get("start_led"), 0), ctx.led_count)
        head = _wrap_index(start_led + int(math.floor(phase * max(1, ctx.led_count - 1) * step_sign)), ctx.led_count)
        trail_length = min(4, ctx.led_count)
        for step in range(trail_length):
            index = _wrap_index(head - (step * step_sign), ctx.led_count)
            frame[index] = blend(_background_color(params), _raw_color_param(params, "color", 0x33AAFF), _decay_factor(step, trail_length, "quadratic"))
        return frame
