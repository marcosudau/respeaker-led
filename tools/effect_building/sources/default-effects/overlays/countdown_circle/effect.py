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


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="countdown_circle",
        title="Countdown Ring",
        description="Stellt einen Countdown als normale temporale Overlay-Effektklasse dar.",
        definition_type=DefinitionType.OVERLAY,
        overlay_mode=OverlayMode.TIMED,
        parameter_schema={
            "total_ms": EffectParamDefinition(name="total_ms", type="duration_ms", default=1000, minimum=1, unit="ms"),
            "deadline_ts": EffectParamDefinition(name="deadline_ts", type="float", required=False),
            "color": EffectParamDefinition(name="color", type="color", default="#FF9F1A"),
            "secondary_color": EffectParamDefinition(name="secondary_color", type="color", default="#FFF3D1"),
            "brightness": EffectParamDefinition(name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0, unit="ratio"),
        },
        defaults={"total_ms": 1000, "color": "#FF9F1A", "secondary_color": "#FFF3D1", "brightness": 1.0},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_transparency=True,
            supports_duration_override=True,
        ),
        layer_rules={
            LayerId.TEMP_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
                requires_finite_duration=True,
                allows_transparency=True,
            ),
        },
        color_model=ColorModel.DUAL,
        composition=CompositionMode.TRANSPARENT,
        animated=False,
        directional=False,
        tags=("builtin", "overlay", "countdown"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        total_ms = max(1, _parse_int(params.get("total_ms"), max(ctx.invocation.requested_duration_ms or 1, 1)))
        deadline_ts = params.get("deadline_ts")
        if deadline_ts is None:
            elapsed_ms = max(0, int(round((ctx.now - ctx.invocation.created_at) * 1000.0)))
            remaining_ms = max(0, (ctx.invocation.requested_duration_ms or total_ms) - elapsed_ms)
        else:
            remaining_ms = max(0, int(round((float(deadline_ts) - ctx.now) * 1000.0)))
        remaining_ratio = max(0.0, min(1.0, remaining_ms / float(total_ms)))
        active_leds = max(0, min(ctx.led_count, int(round(remaining_ratio * ctx.led_count))))
        color = _parse_color(params.get("color"), 0xFF9F1A)
        secondary_color = _parse_color(params.get("secondary_color"), 0xFFF3D1)
        brightness = min(1.0, max(0.0, float(params.get("brightness", 1.0))))
        if brightness < 1.0:
            color = scale_color(color, brightness)
            secondary_color = scale_color(secondary_color, brightness)
        colors: list[int | None] = [None] * ctx.led_count
        for index in range(active_leds):
            colors[index] = color
        if active_leds < ctx.led_count:
            colors[active_leds % ctx.led_count] = secondary_color
        return colors
