from __future__ import annotations

import math

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


def _scale(color: int, factor: float) -> int:
    factor = max(0.0, min(1.0, factor))
    return (
        (int(((color >> 16) & 0xFF) * factor) << 16)
        | (int(((color >> 8) & 0xFF) * factor) << 8)
        | int((color & 0xFF) * factor)
    )


class ExampleShortPulseEvent(BaseEffect):
    definition = EffectDefinition(
        id="example_short_pulse_event",
        title="Example Short Pulse Event",
        description="Tutorial-Event mit einem einmaligen Helligkeitspuls.",
        definition_type=DefinitionType.EVENT,
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "brightness": EffectParamDefinition(
                name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0
            ),
            "duration_ms": EffectParamDefinition(
                name="duration_ms", type="duration_ms", default=600, minimum=100, maximum=5000
            ),
            "speed": EffectParamDefinition(
                name="speed", type="float", default=1.0, minimum=0.1, maximum=10.0
            ),
        },
        defaults={"color": "#33AAFF", "brightness": 1.0, "duration_ms": 600, "speed": 1.0},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_duration_override=True,
            supports_queueing=True,
        ),
        layer_rules={
            LayerId.EVENT_LAYER: LayerRule(
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
                requires_finite_duration=True,
                queue_mode=QueueMode.PRIORITY_FIFO,
            )
        },
        color_model=ColorModel.MONO,
        composition=CompositionMode.OPAQUE,
        animated=True,
        tags=("tutorial", "event", "pulse"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = {**ctx.definition.defaults, **ctx.params}
        duration_ms = ctx.invocation.requested_duration_ms or int(params["duration_ms"])
        elapsed_ms = max(0.0, (ctx.now - ctx.invocation.created_at) * 1000.0)
        progress = min(1.0, elapsed_ms / max(1, duration_ms))
        pulse_progress = min(1.0, progress * float(params["speed"]))
        intensity = math.sin(math.pi * pulse_progress) * float(params["brightness"])
        color = _scale(_color(params["color"]), intensity)
        return [color] * ctx.led_count
