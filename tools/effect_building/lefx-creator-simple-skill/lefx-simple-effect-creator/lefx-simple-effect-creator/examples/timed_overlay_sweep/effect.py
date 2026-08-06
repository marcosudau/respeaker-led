from __future__ import annotations

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
    OverlayMode,
    PlaybackMode,
    RenderContext,
)


def _color(value: str) -> int:
    return int(value.removeprefix("#"), 16)


class ExampleTimedSweepOverlay(BaseEffect):
    definition = EffectDefinition(
        id="example_timed_sweep_overlay",
        title="Example Timed Sweep Overlay",
        description="Transparenter Sweep, der den Ring einmal in fester Zeit durchlaeuft.",
        definition_type=DefinitionType.OVERLAY,
        overlay_mode=OverlayMode.TIMED,
        parameter_schema={
            "color": EffectParamDefinition(
                name="color", type="color", default="#FFD166"
            ),
            "brightness": EffectParamDefinition(
                name="brightness",
                type="float",
                default=0.9,
                minimum=0.0,
                maximum=1.0,
                unit="ratio",
            ),
            "width": EffectParamDefinition(
                name="width", type="int", default=2, minimum=1, maximum=12
            ),
            "duration_ms": EffectParamDefinition(
                name="duration_ms",
                type="duration_ms",
                default=1200,
                minimum=100,
                maximum=10000,
                unit="ms",
            ),
            "reverse": EffectParamDefinition(
                name="reverse", type="bool", default=False
            ),
        },
        defaults={
            "color": "#FFD166",
            "brightness": 0.9,
            "width": 2,
            "duration_ms": 1200,
            "reverse": False,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_transparency=True,
            supports_duration_override=True,
        ),
        layer_rules={
            LayerId.TEMP_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
                requires_finite_duration=True,
                allows_transparency=True,
            ),
        },
        color_model=ColorModel.MONO,
        composition=CompositionMode.TRANSPARENT,
        animated=False,
        directional=True,
        tags=("example", "overlay", "timed", "sweep"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        if ctx.led_count <= 0:
            return []

        params = {**ctx.definition.defaults, **ctx.params}
        duration_ms = ctx.invocation.requested_duration_ms or int(
            params["duration_ms"]
        )
        elapsed_ms = max(
            0.0,
            (ctx.now - ctx.invocation.created_at) * 1000.0,
        )
        progress = min(1.0, elapsed_ms / max(1, duration_ms))

        last_index = ctx.led_count - 1
        center = int(round(progress * last_index))
        if bool(params["reverse"]):
            center = last_index - center

        frame: list[int | None] = [None] * ctx.led_count
        color = scale_color(
            _color(str(params["color"])),
            float(params["brightness"]),
        )
        width = max(1, min(int(params["width"]), ctx.led_count))
        first_offset = -(width // 2)
        for step in range(width):
            frame[(center + first_offset + step) % ctx.led_count] = color
        return frame
