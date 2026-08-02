from __future__ import annotations

from src.core.effect_schema import (
    BaseEffect,
    ColorModel,
    CompositionMode,
    DefinitionType,
    EffectCapabilities,
    EffectDefinition,
    EffectParamDefinition,
    InputContext,
    InputMode,
    InputSamplingPolicy,
    LayerId,
    LayerRule,
    OverlayMode,
    PlaybackMode,
    RenderContext,
)


class TemplateOverlayPullEffect(BaseEffect):
    definition = EffectDefinition(
        id="template_overlay_pull",  # TODO: use a globally unique ID.
        title="Template Pull Overlay",
        description="TODO: describe the locally sampled value.",
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
        input_sampling=InputSamplingPolicy(mode=InputMode.PULL, interval_ms=100),
        tags=("template", "overlay", "pull"),
    )

    def sample_inputs(self, ctx: InputContext) -> dict[str, float] | None:
        # TODO: replace this deterministic sample with the package-local data source.
        return {"value": float(ctx.previous_inputs.get("value", 0.0))}

    def render(self, ctx: RenderContext) -> list[int | None]:
        # TODO: convert the sampled value into a transparent LED frame.
        frame: list[int | None] = [None] * ctx.led_count
        if ctx.inputs.get("value") is not None:
            frame[0] = int(str(ctx.params["color"]).removeprefix("#"), 16)
        return frame
