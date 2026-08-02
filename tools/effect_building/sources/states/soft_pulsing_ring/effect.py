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


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _speed(params: dict[str, Any], default: float) -> float:
    return default * max(0.1, _parse_float(params.get("speed"), 1.0))


def _cycle_phase(now: float, speed: float) -> float:
    if speed <= 0.0:
        return 0.0
    return (now * speed) % 1.0


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="soft_pulsing_ring",
        definition_type=DefinitionType.STATE,
        title="Soft Pulsing Ring",
        description="Weich pulsierender Ring zwischen minimaler und maximaler Helligkeit.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=1.0, minimum=0.1, maximum=10.0, unit="multiplier"),
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "min_brightness": EffectParamDefinition(name="min_brightness", type="float", default=0.05, minimum=0.0, maximum=1.0),
            "brightness": _brightness_param(),
        },
        defaults={
            "speed": 1.0,
            "color": "#33AAFF",
            "background_color": "#000000",
            "min_brightness": 0.05,
            "brightness": 1.0,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        color_model=ColorModel.MONO,
        composition=CompositionMode.OPAQUE,
        animated=True,
        directional=False,
        tags=("builtin", "state", "animated", "pulse"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        phase = _cycle_phase(ctx.now, _speed(params, 0.7))
        mix = 0.5 - 0.5 * math.cos(2.0 * math.pi * phase)
        min_brightness = _clamp01(_parse_float(params.get("min_brightness"), 0.05))
        brightness = max(min_brightness, _brightness(params, 1.0))
        intensity = min_brightness + ((brightness - min_brightness) * mix)
        color = _raw_color_param(params, "color", 0x33AAFF)
        background = _background_color(params)
        return [blend(background, color, intensity)] * ctx.led_count
