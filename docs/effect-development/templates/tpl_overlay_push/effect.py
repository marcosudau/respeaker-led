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


class TemplateOverlayPushEffect(BaseEffect):
    definition = EffectDefinition(
        id="template_overlay_push",  # TODO: use a globally unique ID.
        title="Template Push Overlay",  # TODO: choose a user-facing title.
        description="TODO: describe the information shown by this overlay.",
        definition_type=DefinitionType.OVERLAY,
        overlay_mode=OverlayMode.CONTROLLED,
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "brightness": EffectParamDefinition(
                name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0
            ),
        },
        runtime_input_schema={
            "value": EffectParamDefinition(
                name="value", type="float", required=False, nullable=True
            )
        },
        defaults={"color": "#33AAFF", "brightness": 1.0},
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
        input_sampling=InputSamplingPolicy(mode=InputMode.PUSH),
        tags=("template", "overlay", "push"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        # TODO: render only the LEDs owned by the overlay; keep all others None.
        frame: list[int | None] = [None] * ctx.led_count
        if ctx.inputs.get("value") is not None:
            frame[0] = int(str(ctx.params["color"]).removeprefix("#"), 16)
        return frame
