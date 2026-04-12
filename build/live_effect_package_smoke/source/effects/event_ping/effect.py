from src.core.effect_schema import BaseEffect, EffectCapabilities, EffectDefinition, EffectParamDefinition, LayerId, LayerRule, PlaybackMode, RenderContext


class EventPingEffect(BaseEffect):
    definition = EffectDefinition(
        id="event_ping",
        title="EventPingEffect",
        description="Live smoke-test effect",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="0x33D1FF"),
        },
        defaults={"color": "0x33D1FF"},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            restorable=False,
        ),
        layer_rules={
            LayerId.EVENT_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
                requires_finite_duration=True,
            ),
        },
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        raw_color = str(ctx.params.get("color", "0x33D1FF")).replace("#", "0x")
        base_color = int(raw_color, 16)
        phase = int(ctx.now * 12 + 0) % 2
        current = base_color if phase == 0 else 0
        return [current] * ctx.led_count
