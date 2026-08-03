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


def _parse_gradient(value: Any, default: list[int]) -> list[int]:
    if value is None:
        return list(default)
    if isinstance(value, str):
        raw_values = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, (list, tuple)):
        raw_values = list(value)
    else:
        return list(default)

    colors: list[int] = []
    for item in raw_values:
        try:
            raw_color = item.get("color") if isinstance(item, dict) else item
            colors.append(_parse_color(raw_color, 0))
        except (TypeError, ValueError):
            continue
    return colors or list(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _speed(params: dict[str, Any], default: float) -> float:
    return default * max(0.1, _parse_float(params.get("speed"), 1.0))


def _palette_sample(colors: list[int], factor: float) -> int:
    if not colors:
        return 0
    if len(colors) == 1:
        return colors[0]
    position = _clamp01(factor) * (len(colors) - 1)
    left = int(math.floor(position))
    right = min(len(colors) - 1, left + 1)
    mix = position - left
    return blend(colors[left], colors[right], mix)


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="rotating_gradient",
        definition_type=DefinitionType.STATE,
        title="Rotating Gradient",
        description="Rotierender Farbverlauf ueber den gesamten Ring.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=1.0, minimum=0.1, maximum=10.0, unit="multiplier"),
            "gradient": EffectParamDefinition(
                name="gradient",
                type="gradient",
                default=(
                    {"at": 0.0, "color": "#33AAFF"},
                    {"at": 1.0, "color": "#FFAA33"},
                ),
            ),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "reverse": _reverse_param(),
        },
        defaults={
            "speed": 1.0,
            "gradient": (
                {"at": 0.0, "color": "#33AAFF"},
                {"at": 1.0, "color": "#FFAA33"},
            ),
            "background_color": "#000000",
            "brightness": 1.0,
            "reverse": False,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        color_model=ColorModel.GRADIENT,
        composition=CompositionMode.OPAQUE,
        animated=True,
        directional=True,
        tags=("builtin", "state", "animated", "gradient"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        palette = _parse_gradient(params.get("gradient"), [0x33AAFF, 0xFFAA33])
        if not palette:
            return [_background_color(params)] * ctx.led_count
        brightness = _brightness(params, 1.0)
        if brightness < 1.0:
            palette = [scale_color(color, brightness) for color in palette]
        step_sign = _step_sign(params)
        shift = ctx.now * _speed(params, 1.0) * step_sign
        frame: list[int | None] = []
        denominator = max(1, ctx.led_count - 1)
        for led_index in range(ctx.led_count):
            sample = (led_index - shift) % ctx.led_count
            frame.append(_palette_sample(palette, sample / float(denominator)))
        return frame
