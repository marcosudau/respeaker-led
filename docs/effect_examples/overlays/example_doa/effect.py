from __future__ import annotations

from src.core.effect_schema import (
    BaseEffect,
    ColorModel,
    CompositionMode,
    DefinitionType,
    EffectCapabilities,
    EffectDefinition,
    EffectParamDefinition,
    InputMode,
    InputSamplingPolicy,
    LayerId,
    LayerRule,
    OverlayMode,
    PlaybackMode,
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


class ExampleDoaOverlay(BaseEffect):
    definition = EffectDefinition(
        id="example_doa_overlay",
        title="Example DoA Overlay",
        description="Tutorial-Overlay fuer extern gelieferte ReSpeaker-Richtungswerte.",
        definition_type=DefinitionType.OVERLAY,
        overlay_mode=OverlayMode.CONTROLLED,
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33FFAA"),
            "brightness": EffectParamDefinition(
                name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0
            ),
            "width": EffectParamDefinition(
                name="width", type="int", default=1, minimum=1, maximum=5
            ),
        },
        runtime_input_schema={
            "direction_deg": EffectParamDefinition(
                name="direction_deg",
                type="angle_deg",
                required=False,
                nullable=True,
                unit="deg",
                aliases=("direction",),
            )
        },
        defaults={"color": "#33FFAA", "brightness": 1.0, "width": 1},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_transparency=True,
            restorable=True,
            data_driven=True,
        ),
        layer_rules={
            LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                requires_indefinite_duration=True,
                allows_transparency=True,
            )
        },
        color_model=ColorModel.MONO,
        composition=CompositionMode.TRANSPARENT,
        directional=False,
        input_sampling=InputSamplingPolicy(
            mode=InputMode.PUSH,
            heartbeat_interval_ms=1000,
            max_missed_heartbeats=3,
        ),
        tags=("tutorial", "overlay", "doa"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        direction = ctx.inputs.get("direction_deg")
        frame: list[int | None] = [None] * ctx.led_count
        if direction is None:
            return frame

        params = {**ctx.definition.defaults, **ctx.params}
        center = round((float(direction) % 360.0) / 360.0 * ctx.led_count) % ctx.led_count
        color = _scale(_color(params["color"]), float(params["brightness"]))
        width = min(int(params["width"]), ctx.led_count)
        for offset in range(-(width // 2), width - (width // 2)):
            frame[(center + offset) % ctx.led_count] = color
        return frame
