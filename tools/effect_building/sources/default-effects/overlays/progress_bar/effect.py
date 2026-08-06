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


def _param_value(params: dict[str, Any], key: str, *aliases: str) -> Any:
    for candidate in (key, *aliases):
        if candidate in params:
            return params.get(candidate)
    return None


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


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="progress_bar",
        title="Progress Bar",
        description="Bildet einen Fortschritt ringfoermig als normale Effektklasse ab.",
        definition_type=DefinitionType.OVERLAY,
        overlay_mode=OverlayMode.CONTROLLED,
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#050505"),
            "brightness": EffectParamDefinition(name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0, unit="ratio"),
        },
        runtime_input_schema={
            "progress": EffectParamDefinition(
                name="progress",
                type="float",
                default=0.0,
                minimum=0.0,
                maximum=100.0,
                aliases=("value",),
            ),
        },
        defaults={"color": "#33AAFF", "background_color": "#050505", "brightness": 1.0},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules={
            LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                requires_indefinite_duration=True,
            ),
        },
        color_model=ColorModel.MONO,
        composition=CompositionMode.TRANSPARENT,
        animated=False,
        directional=False,
        input_sampling=InputSamplingPolicy(),
        tags=("builtin", "progress"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        value = min(100.0, max(0.0, _parse_float(params.get("progress"), 0.0)))
        active_leds = int(round((value / 100.0) * ctx.led_count))
        color = _parse_color(params.get("color"), 0x33AAFF)
        background_color = _parse_color(_param_value(params, "background_color", "base_color"), 0x050505)
        brightness = min(1.0, max(0.0, _parse_float(params.get("brightness"), 1.0)))
        if brightness < 1.0:
            color = scale_color(color, brightness)
            background_color = scale_color(background_color, brightness)
        return [color if index < active_leds else background_color for index in range(ctx.led_count)]
