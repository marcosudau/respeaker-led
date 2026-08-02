from __future__ import annotations

from src.core.effect_schema import (
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


def _scale(color: int, factor: float) -> int:
    factor = max(0.0, min(1.0, factor))
    red = int(((color >> 16) & 0xFF) * factor)
    green = int(((color >> 8) & 0xFF) * factor)
    blue = int((color & 0xFF) * factor)
    return (red << 16) | (green << 8) | blue


class ExampleRotationState(BaseEffect):
    definition = EffectDefinition(
        id="example_rotation_state",
        title="Example Rotation State",
        description="Tutorial-State mit einem dauerhaft rotierenden Segment.",
        definition_type=DefinitionType.STATE,
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(
                name="background_color", type="color", default="#000000"
            ),
            "brightness": EffectParamDefinition(
                name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0
            ),
            "speed": EffectParamDefinition(
                name="speed", type="float", default=1.0, minimum=0.1, maximum=10.0
            ),
            "reverse": EffectParamDefinition(name="reverse", type="bool", default=False),
            "segment_length": EffectParamDefinition(
                name="segment_length", type="int", default=3, minimum=1, maximum=12
            ),
        },
        defaults={
            "color": "#33AAFF",
            "background_color": "#000000",
            "brightness": 1.0,
            "speed": 1.0,
            "reverse": False,
            "segment_length": 3,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules={
            LayerId.STATE_LAYER: LayerRule(
                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                requires_indefinite_duration=True,
            )
        },
        color_model=ColorModel.MONO,
        composition=CompositionMode.OPAQUE,
        animated=True,
        directional=True,
        tags=("tutorial", "state", "rotation"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = {**ctx.definition.defaults, **ctx.params}
        elapsed = max(0.0, ctx.now - ctx.invocation.created_at)
        direction = -1 if params["reverse"] else 1
        head = int(elapsed * float(params["speed"]) * 4.0 * direction) % ctx.led_count
        foreground = _scale(_color(params["color"]), float(params["brightness"]))
        frame: list[int | None] = [_color(params["background_color"])] * ctx.led_count
        for offset in range(min(int(params["segment_length"]), ctx.led_count)):
            frame[(head + (offset * direction)) % ctx.led_count] = foreground
        return frame
