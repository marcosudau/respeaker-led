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


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="solid_color",
        title="Solid Color",
        description="Faerbt den gesamten Ziel-Layer statisch ein.",
        definition_type=DefinitionType.STATE,
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "brightness": EffectParamDefinition(name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0),
        },
        defaults={"color": "#33AAFF", "brightness": 1.0},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_persistent_state_rules(),
        color_model=ColorModel.MONO,
        composition=CompositionMode.OPAQUE,
        animated=False,
        directional=False,
        tags=("builtin", "state"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        color = _parse_color(params.get("color"), 0)
        brightness = min(1.0, max(0.0, _parse_float(params.get("brightness"), 1.0)))
        color = scale_color(color, brightness)
        return [color] * ctx.led_count
