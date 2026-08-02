from __future__ import annotations

from src.core.effect_schema import BaseEffect, ColorModel, DefinitionType, EffectCapabilities, EffectDefinition, EffectParamDefinition, LayerId, LayerRule, OverlayMode, PlaybackMode, RenderContext


class TemplateOverlayTimedEffect(BaseEffect):
    definition = EffectDefinition(
        id="template_overlay_timed",
        title="Template Timed Overlay",
        description="TODO: describe this definition.",
        definition_type=DefinitionType.OVERLAY,
        overlay_mode=OverlayMode.TIMED,
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "brightness": EffectParamDefinition(name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0, unit="ratio"),
            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=1000, minimum=1, unit="ms"),
        },
        defaults={"color": "#33AAFF", "brightness": 1.0, "duration_ms": 1000},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            restorable=True,
        ),
        layer_rules={
            LayerId.TEMP_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
                requires_finite_duration=True,
            ),
        },
        color_model=ColorModel.MONO,
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        raw_color = str(ctx.params.get("color", "#33AAFF")).replace("#", "0x")
        color = int(raw_color, 16)
        return [color] * ctx.led_count
