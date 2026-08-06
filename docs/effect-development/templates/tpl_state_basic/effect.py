from __future__ import annotations

from respeaker_led.core.effect_schema import BaseEffect, ColorModel, DefinitionType, EffectCapabilities, EffectDefinition, EffectParamDefinition, LayerId, LayerRule, OverlayMode, PlaybackMode, RenderContext


class TemplateStateEffect(BaseEffect):
    definition = EffectDefinition(
        id="template_state",
        title="Template State",
        description="TODO: describe this definition.",
        definition_type=DefinitionType.STATE,
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "brightness": EffectParamDefinition(name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0, unit="ratio"),
        },
        defaults={"color": "#33AAFF", "brightness": 1.0},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules={
            LayerId.STATE_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                requires_indefinite_duration=True,
            ),
        },
        color_model=ColorModel.MONO,
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        raw_color = str(ctx.params.get("color", "#33AAFF")).replace("#", "0x")
        color = int(raw_color, 16)
        return [color] * ctx.led_count
