from src.core.effect_schema import BaseEffect, EffectCapabilities, EffectDefinition, EffectParamDefinition, LayerId, LayerRule, PlaybackMode, RenderContext


class StateIdleEffect(BaseEffect):
    definition = EffectDefinition(
        id="state_idle",
        title="StateIdleEffect",
        description="Live smoke-test effect",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="0x224466"),
        },
        defaults={"color": "0x224466"},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules={
            LayerId.STATE_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                requires_finite_duration=False,
            ),
        },
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        raw_color = str(ctx.params.get("color", "0x224466")).replace("#", "0x")
        base_color = int(raw_color, 16)
        return [base_color] * ctx.led_count
