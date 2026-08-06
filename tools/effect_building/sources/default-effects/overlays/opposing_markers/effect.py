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


def _overlay_rules() -> dict[LayerId, LayerRule]:
    return {
        LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            requires_indefinite_duration=True,
            allows_transparency=True,
        ),
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


def _wrap_index(index: int, led_count: int) -> int:
    return index % max(1, led_count)


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="opposing_markers",
        definition_type=DefinitionType.OVERLAY,
        overlay_mode=OverlayMode.CONTROLLED,
        title="Opposing Markers",
        description="Zwei gegensaetzliche Marker mit eigener Position und Farbe.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "secondary_color": EffectParamDefinition(name="secondary_color", type="color", default="#FFAA33"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
        },
        runtime_input_schema={
            "position_a": EffectParamDefinition(name="position_a", type="int", default=0, minimum=0),
            "position_b": EffectParamDefinition(name="position_b", type="int", required=False, minimum=0),
        },
        defaults={
            "color": "#33AAFF",
            "secondary_color": "#FFAA33",
            "background_color": "#000000",
            "brightness": 1.0,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_transparency=True,
            restorable=True,
        ),
        layer_rules=_overlay_rules(),
        color_model=ColorModel.DUAL,
        composition=CompositionMode.TRANSPARENT,
        animated=False,
        directional=False,
        input_sampling=InputSamplingPolicy(),
        tags=("builtin", "overlay", "markers"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame = [_background_color(params)] * ctx.led_count
        position_a = _wrap_index(_parse_int(params.get("position_a"), 0), ctx.led_count)
        default_b = position_a + (ctx.led_count // 2)
        position_b = _wrap_index(_parse_int(params.get("position_b"), default_b), ctx.led_count)
        frame[position_a] = _color_param(params, "color", 0x33AAFF)
        frame[position_b] = _color_param(params, "secondary_color", 0xFFAA33)
        return frame
