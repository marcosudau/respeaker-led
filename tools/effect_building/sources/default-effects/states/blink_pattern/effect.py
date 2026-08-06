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


_PATTERN_ENUM = ("single", "double", "triple", "continuous")


def _state_rules() -> dict[LayerId, LayerRule]:
    return _persistent_state_rules()


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


def _speed(params: dict[str, Any], default: float) -> float:
    return default * max(0.1, _parse_float(params.get("speed"), 1.0))


def _cycle_phase(now: float, speed: float) -> float:
    if speed <= 0.0:
        return 0.0
    return (now * speed) % 1.0


def _pattern_centers(pattern: str) -> list[float]:
    if pattern == "double":
        return [0.18, 0.52]
    if pattern == "triple":
        return [0.12, 0.38, 0.64]
    if pattern == "continuous":
        return []
    return [0.2]


def _pattern_intensity(phase: float, pattern: str, *, soft: bool) -> float:
    normalized = _clamp01(phase)
    if pattern == "continuous":
        return 0.5 - 0.5 * math.cos(2.0 * math.pi * normalized) if soft else (1.0 if normalized < 0.5 else 0.0)

    width = {"single": 0.22, "double": 0.16, "triple": 0.12}.get(pattern, 0.22)
    best = 0.0
    for center in _pattern_centers(pattern):
        distance = abs(normalized - center)
        if distance > width:
            continue
        local = 1.0 - (distance / width)
        if soft:
            local = 0.5 - 0.5 * math.cos(math.pi * local)
        else:
            local = 1.0
        best = max(best, local)
    return best


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="blink_pattern",
        definition_type=DefinitionType.STATE,
        title="Blink Pattern",
        description="Einfaches, doppeltes, dreifaches oder dauerhaftes Blinken.",
        parameter_schema={
            "pattern": EffectParamDefinition(name="pattern", type="enum", default="single", enum_values=_PATTERN_ENUM),
            "speed": EffectParamDefinition(name="speed", type="float", default=1.0, minimum=0.1, maximum=10.0, unit="multiplier"),
            "color": EffectParamDefinition(name="color", type="color", default="#FFAA33"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
        },
        defaults={"pattern": "single", "speed": 1.0, "color": "#FFAA33", "background_color": "#000000", "brightness": 1.0},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        color_model=ColorModel.MONO,
        composition=CompositionMode.OPAQUE,
        animated=True,
        directional=False,
        tags=("builtin", "state", "animated", "blink"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        intensity = _pattern_intensity(
            _cycle_phase(ctx.now, _speed(params, 1.0)),
            str(params.get("pattern", "single")).strip().lower(),
            soft=False,
        )
        return [(_color_param(params, "color", 0xFFAA33) if intensity > 0.0 else _background_color(params))] * ctx.led_count
