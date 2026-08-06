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
    RenderContext,
)


BASE_STEPS_PER_SECOND = 4.0


def _color(value: str) -> int:
    return int(value.removeprefix("#"), 16)


class ExampleRotatingSegmentState(BaseEffect):
    definition = EffectDefinition(
        id="example_rotating_segment_state",
        title="Example Rotating Segment State",
        description="Dauerhaft rotierendes Segment mit einstellbarer Breite.",
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
                default=0.7,
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
            "segment_length": EffectParamDefinition(
                name="segment_length",
                type="int",
                default=4,
                minimum=1,
            ),
            "reverse": EffectParamDefinition(
                name="reverse", type="bool", default=False
            ),
        },
        defaults={
            "color": "#4A7BFF",
            "background_color": "#020814",
            "brightness": 0.7,
            "speed": 1.0,
            "segment_length": 4,
            "reverse": False,
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
        directional=True,
        tags=("example", "state", "rotation", "segment"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        if ctx.led_count <= 0:
            return []

        params = {**ctx.definition.defaults, **ctx.params}
        elapsed = max(0.0, ctx.now - ctx.invocation.created_at)
        direction = -1 if bool(params["reverse"]) else 1

        steps = int(
            math.floor(
                elapsed * BASE_STEPS_PER_SECOND * float(params["speed"])
            )
        )
        head = (steps * direction) % ctx.led_count

        background = scale_color(
            _color(str(params["background_color"])),
            float(params["brightness"]),
        )
        foreground = scale_color(
            _color(str(params["color"])),
            float(params["brightness"]),
        )
        frame: list[int | None] = [background] * ctx.led_count

        length = max(1, min(int(params["segment_length"]), ctx.led_count))
        for offset in range(length):
            index = (head - direction * offset) % ctx.led_count
            frame[index] = foreground
        return frame
