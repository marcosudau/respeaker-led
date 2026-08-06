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


def _parse_float(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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


def _brightness(params: dict[str, Any], default: float = 1.0) -> float:
    return _clamp01(_parse_float(params.get("brightness"), default))


def _color_param(
    params: dict[str, Any],
    key: str,
    default: int,
    *aliases: str,
) -> int:
    color = _raw_color_param(params, key, default, *aliases)
    brightness = _brightness(params, 1.0)
    return color if brightness >= 1.0 else scale_color(color, brightness)


def _background_color(params: dict[str, Any], default: int = 0x000000) -> int:
    return _raw_color_param(params, "background_color", default, "base_color")


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _event_duration_ms(ctx: RenderContext, params: dict[str, Any], default_ms: int) -> int:
    requested = ctx.invocation.requested_duration_ms
    if requested is None:
        requested = _parse_int(params.get("duration_ms"), default_ms)
    return max(1, int(requested))


def _elapsed_fraction(ctx: RenderContext, params: dict[str, Any], default_ms: int) -> float:
    duration_ms = _event_duration_ms(ctx, params, default_ms)
    elapsed_ms = max(0.0, (ctx.now - ctx.invocation.created_at) * 1000.0)
    return _clamp01(elapsed_ms / float(duration_ms))


def _sparkle_indices(invocation_id: str, bucket: int, led_count: int, count: int) -> list[int]:
    scored: list[tuple[str, int]] = []
    for led_index in range(led_count):
        digest = hashlib.sha1(f"{invocation_id}:{bucket}:{led_index}".encode("utf-8")).hexdigest()
        scored.append((digest, led_index))
    scored.sort()
    return [led_index for _, led_index in scored[: max(0, min(count, led_count))]]


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="sparkle_burst",
        definition_type=DefinitionType.EVENT,
        title="Sparkle Burst",
        description="Kurzer Sparkle-Effekt mit zufaelligen LEDs ueber den Event-Layer.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#FFFFFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "sparkle_count": EffectParamDefinition(name="sparkle_count", type="int", default=3, minimum=1),
            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=650, minimum=1, unit="ms"),
        },
        defaults={"color": "#FFFFFF", "background_color": "#000000", "brightness": 1.0, "sparkle_count": 3, "duration_ms": 650},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
        ),
        layer_rules=_event_rules(),
        color_model=ColorModel.MONO,
        composition=CompositionMode.OPAQUE,
        animated=False,
        directional=False,
        tags=("builtin", "event", "sparkle"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame = [_background_color(params)] * ctx.led_count
        bucket = int(math.floor(_elapsed_fraction(ctx, params, 650) * 8.0))
        for led_index in _sparkle_indices(
            ctx.invocation.invocation_id,
            bucket,
            ctx.led_count,
            _parse_int(params.get("sparkle_count", params.get("random_led_count")), 3),
        ):
            frame[led_index] = _color_param(params, "color", 0xFFFFFF)
        return frame
