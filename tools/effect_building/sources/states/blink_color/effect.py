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


def _parse_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
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


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="blink_color",
        title="Blink Color",
        description="Blinkt zwischen Akzent- und Grundfarbe.",
        definition_type=DefinitionType.STATE,
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#FFAA00"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": EffectParamDefinition(name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0, unit="ratio"),
            "speed": EffectParamDefinition(name="speed", type="float", default=1.0, minimum=0.1, maximum=10.0, unit="multiplier"),
            "duty_cycle": EffectParamDefinition(name="duty_cycle", type="float", default=0.5, minimum=0.0, maximum=1.0),
        },
        defaults={"color": "#FFAA00", "background_color": "#000000", "brightness": 1.0, "speed": 1.0, "duty_cycle": 0.5},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_queueing=True,
            restorable=True,
        ),
        layer_rules=_persistent_state_rules(),
        color_model=ColorModel.MONO,
        composition=CompositionMode.OPAQUE,
        animated=True,
        directional=False,
        tags=("builtin", "animated"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        color = _parse_color(params.get("color"), 0xFFAA00)
        background_color = _parse_color(_param_value(params, "background_color", "base_color"), 0x000000)
        speed = max(0.1, _parse_float(params.get("speed"), 1.0))
        period_ms = max(1.0, 900.0 / speed)
        duty_cycle = min(1.0, max(0.0, _parse_float(params.get("duty_cycle"), 0.5)))
        phase = ((ctx.now * 1000.0) % period_ms) / float(period_ms)
        frame_color = color if phase < duty_cycle else background_color
        brightness = min(1.0, max(0.0, _parse_float(params.get("brightness"), 1.0)))
        if brightness < 1.0:
            frame_color = scale_color(frame_color, brightness)
        return [frame_color] * ctx.led_count
