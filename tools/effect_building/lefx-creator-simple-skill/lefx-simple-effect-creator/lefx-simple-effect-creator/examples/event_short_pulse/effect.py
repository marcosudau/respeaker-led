from __future__ import annotations

import math

from respeaker_led.core.color_math import scale_color
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
    QueueMode,
    RenderContext,
)


def _color(value: str) -> int:
    return int(value.removeprefix("#"), 16)


class ExampleShortPulseEvent(BaseEffect):
    definition = EffectDefinition(
        id="example_short_pulse_event",
        title="Example Short Pulse Event",
        description="Einmaliger Helligkeitspuls ueber den gesamten Ring.",
        definition_type=DefinitionType.EVENT,
        parameter_schema={
            "color": EffectParamDefinition(
                name="color", type="color", default="#42D392"
            ),
            "brightness": EffectParamDefinition(
                name="brightness",
                type="float",
                default=0.9,
                minimum=0.0,
                maximum=1.0,
                unit="ratio",
            ),
            "duration_ms": EffectParamDefinition(
                name="duration_ms",
                type="duration_ms",
                default=600,
                minimum=100,
                maximum=5000,
                unit="ms",
            ),
            "speed": EffectParamDefinition(
                name="speed",
                type="float",
                default=1.0,
                minimum=0.1,
                maximum=10.0,
                unit="multiplier",
            ),
        },
        defaults={
            "color": "#42D392",
            "brightness": 0.9,
            "duration_ms": 600,
            "speed": 1.0,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_duration_override=True,
            supports_queueing=True,
        ),
        layer_rules={
            LayerId.EVENT_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
                requires_finite_duration=True,
                queue_mode=QueueMode.PRIORITY_FIFO,
            ),
        },
        color_model=ColorModel.MONO,
        composition=CompositionMode.OPAQUE,
        animated=True,
        directional=False,
        tags=("example", "event", "pulse"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = {**ctx.definition.defaults, **ctx.params}
        duration_ms = ctx.invocation.requested_duration_ms or int(
            params["duration_ms"]
        )
        elapsed_ms = max(
            0.0,
            (ctx.now - ctx.invocation.created_at) * 1000.0,
        )
        progress = min(1.0, elapsed_ms / max(1, duration_ms))

        pulse_progress = min(1.0, progress * float(params["speed"]))
        intensity = max(0.0, math.sin(math.pi * pulse_progress))
        intensity *= float(params["brightness"])

        color = scale_color(_color(str(params["color"])), intensity)
        return [color] * ctx.led_count
