from __future__ import annotations

import hashlib
import math
from typing import Any

from src.core.color_math import blend, scale_color
from src.core.effect_schema import (
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


def _persistent_state_rules() -> dict[LayerId, LayerRule]:
    return {
        LayerId.BACKGROUND_STATE_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            requires_indefinite_duration=True,
            persistent_storage=True,
        ),
        LayerId.STATE_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            requires_indefinite_duration=True,
        ),
    }


def _state_rules() -> dict[LayerId, LayerRule]:
    return _persistent_state_rules()


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


def _speed(params: dict[str, Any], default: float) -> float:
    return default * max(0.1, _parse_float(params.get("speed"), 1.0))


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="yin_yang_spin",
        definition_type=DefinitionType.STATE,
        title="Yin Yang Spin",
        description="Rotierender Yin-Yang-Effekt mit zwei Farben, Richtung und Trennschaerfe.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=1.0, minimum=0.1, maximum=10.0, unit="multiplier"),
            "color": EffectParamDefinition(name="color", type="color", default="#FFFFFF"),
            "secondary_color": EffectParamDefinition(name="secondary_color", type="color", default="#111111"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "sharpness": EffectParamDefinition(name="sharpness", type="float", default=0.9, minimum=0.0, maximum=1.0),
            "reverse": _reverse_param(),
        },
        defaults={
            "speed": 1.0,
            "color": "#FFFFFF",
            "secondary_color": "#111111",
            "background_color": "#000000",
            "brightness": 1.0,
            "sharpness": 0.9,
            "reverse": False,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        color_model=ColorModel.DUAL,
        composition=CompositionMode.OPAQUE,
        animated=True,
        directional=True,
        tags=("builtin", "state", "animated", "duotone"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        color = _color_param(params, "color", 0xFFFFFF, "color_1")
        secondary_color = _color_param(params, "secondary_color", 0x111111, "color_2")
        background = _background_color(params)
        sharpness = _clamp01(_parse_float(params.get("sharpness", params.get("trennschaerfe")), 0.9))
        soft_zone = max(0.01, (1.0 - sharpness) * 0.5)
        step_sign = _step_sign(params)
        shift = ctx.now * _speed(params, 1.5) * step_sign
        frame: list[int | None] = []
        for led_index in range(ctx.led_count):
            position = ((led_index - shift) % ctx.led_count) / float(max(1, ctx.led_count))
            distance = abs(position - 0.5)
            if distance > soft_zone:
                base = color if position < 0.5 else secondary_color
            else:
                mix = (position - (0.5 - soft_zone)) / float(max(soft_zone * 2.0, 0.0001))
                base = blend(color, secondary_color, _clamp01(mix))
            frame.append(blend(background, base, 1.0))
        return frame
