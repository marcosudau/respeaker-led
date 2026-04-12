from src.core.effect_schema import BaseEffect, EffectCapabilities, EffectDefinition, EffectParamDefinition, LayerId, LayerRule, PlaybackMode, RenderContext


class OverlayWarningEffect(BaseEffect):
    definition = EffectDefinition(
        id="overlay_warning",
        title="OverlayWarningEffect",
        description="Live smoke-test effect",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="0xFFFFFF"),
        },
        defaults={"color": "0xFFFFFF"},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules={
            LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                requires_finite_duration=False,
            ),
        },
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        raw_color = str(ctx.params.get("color", "0xFFFFFF")).replace("#", "0x")
        base_color = int(raw_color, 16)
        leds = [None] * ctx.led_count
        leds[6 % ctx.led_count] = base_color
        leds[(6 + 1) % ctx.led_count] = base_color
        return leds
