from __future__ import annotations

import math

from respeaker_led.core.color_math import blend, scale_color
from respeaker_led.core.effect_schema import (
    BaseEffect,
    ColorModel,
    CompositionMode,
    DefinitionType,
    EffectCapabilities,
    EffectDefinition,
    EffectParamDefinition,
    LayerId,
    LayerRule,
    PlaybackMode,
    RenderContext,
)


def _color(value: str) -> int:
    return int(value.removeprefix("#"), 16)


class ExampleSoftPulseState(BaseEffect):
    definition = EffectDefinition(
        id="example_soft_pulse_state",
        title="Example Soft Pulse State",
        description="Weicher, dauerhaft laufender Puls ueber den gesamten Ring.",
        definition_type=DefinitionType.STATE,
        parameter_schema={
            "color": EffectParamDefinition(
                name="color", type="color", default="#4A7BFF"
            ),
            "background_color": EffectParamDefinition(
                name="background_color", type="color", default="#020814"
            ),
            "brightness": EffectParamDefinition(
                name="brightness",
                type="float",
                default=0.6,
                minimum=0.0,
                maximum=1.0,
                unit="ratio",
            ),
            "speed": EffectParamDefinition(
                name="speed",
                type="float",
                default=1.0,
                minimum=0.1,
                maximum=10.0,
                unit="multiplier",
            ),
            "min_brightness": EffectParamDefinition(
                name="min_brightness",
                type="float",
                default=0.1,
                minimum=0.0,
                maximum=1.0,
                unit="ratio",
            ),
        },
        defaults={
            "color": "#4A7BFF",
            "background_color": "#020814",
            "brightness": 0.6,
            "speed": 1.0,
            "min_brightness": 0.1,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules={
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
        },
        color_model=ColorModel.MONO,
        composition=CompositionMode.OPAQUE,
        animated=True,
        directional=False,
        tags=("example", "state", "pulse"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = {**ctx.definition.defaults, **ctx.params}
        elapsed = max(0.0, ctx.now - ctx.invocation.created_at)

        speed = float(params["speed"])
        period_s = 2.4 / max(0.01, speed)
        phase = (elapsed / period_s) % 1.0
        wave = 0.5 - 0.5 * math.cos(2.0 * math.pi * phase)

        minimum = float(params["min_brightness"])
        pulse_mix = minimum + (1.0 - minimum) * wave
        pulse_mix = max(0.0, min(1.0, pulse_mix))

        foreground = _color(str(params["color"]))
        background = _color(str(params["background_color"]))
        color = blend(background, foreground, pulse_mix)
        color = scale_color(color, float(params["brightness"]))
        return [color] * ctx.led_count
