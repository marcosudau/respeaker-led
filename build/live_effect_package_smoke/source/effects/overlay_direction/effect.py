from src.core.effect_schema import BaseEffect, EffectCapabilities, EffectDefinition, EffectParamDefinition, LayerId, LayerRule, PlaybackMode, RenderContext


class OverlayDirectionEffect(BaseEffect):
    definition = EffectDefinition(
        id="overlay_direction",
        title="OverlayDirectionEffect",
        description="Live smoke-test effect",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="0x55CCFF"),
        },
        defaults={"color": "0x55CCFF"},
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
        raw_color = str(ctx.params.get("color", "0x55CCFF")).replace("#", "0x")
        base_color = int(raw_color, 16)
        leds = [None] * ctx.led_count
        leds[0 % ctx.led_count] = base_color
        leds[(0 + 1) % ctx.led_count] = base_color
        return leds
