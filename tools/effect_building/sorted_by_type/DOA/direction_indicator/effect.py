from __future__ import annotations

from src.core.effect_schema import (
    BaseEffect,
    EffectCapabilities,
    EffectDefinition,
    EffectParamDefinition,
    LayerId,
    LayerRule,
    PlaybackMode,
    QueueMode,
    RenderContext,
)

from .basic import BlinkColorEffect
from .common import _merge_params, _param_value, _parse_color, _parse_float, _parse_int


class DirectionIndicatorEffect(BaseEffect):
    definition = EffectDefinition(
        id="direction_indicator",
        title="Direction Indicator",
        description="Markiert eine Richtung als halbtransparente Ring-Einblendung.",
        parameter_schema={
            "direction": EffectParamDefinition(name="direction", type="float", default=0.0),
            "center_color": EffectParamDefinition(name="center_color", type="color", default="#EAF8FF"),
            "side_color": EffectParamDefinition(name="side_color", type="color", default="#7FC9FF"),
        },
        defaults={"direction": 0.0, "center_color": "#EAF8FF", "side_color": "#7FC9FF"},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_transparency=True,
            restorable=True,
        ),
        layer_rules={
            LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                requires_indefinite_duration=True,
                allows_transparency=True,
            ),
        },
        tags=("builtin", "overlay", "direction"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        direction = _parse_float(_param_value(params, "direction", "direction_deg"), 0.0) % 360.0
        center = int(round((direction / 360.0) * ctx.led_count)) % ctx.led_count
        center_color = _parse_color(params.get("center_color"), 0xEAF8FF)
        side_color = _parse_color(params.get("side_color"), 0x7FC9FF)
        colors: list[int | None] = [None] * ctx.led_count
        colors[center] = center_color
        colors[(center - 1) % ctx.led_count] = side_color
        colors[(center + 1) % ctx.led_count] = side_color
        return colors


class CountdownRingEffect(BaseEffect):
    definition = EffectDefinition(
        id="countdown_ring",
        title="Countdown Ring",
        description="Stellt einen Countdown als normale temporale Overlay-Effektklasse dar.",
        parameter_schema={
            "total_ms": EffectParamDefinition(name="total_ms", type="duration_ms", default=1000, minimum=1, unit="ms"),
            "deadline_ts": EffectParamDefinition(name="deadline_ts", type="float", required=False),
            "color": EffectParamDefinition(name="color", type="color", default="#FF9F1A"),
            "marker_color": EffectParamDefinition(name="marker_color", type="color", default="#FFF3D1"),
        },
        defaults={"total_ms": 1000, "color": "#FF9F1A", "marker_color": "#FFF3D1"},
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
        tags=("builtin", "overlay", "countdown"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        total_ms = max(1, _parse_int(params.get("total_ms"), max(ctx.invocation.requested_duration_ms or 1, 1)))
        deadline_ts = params.get("deadline_ts")
        if deadline_ts is None:
            elapsed_ms = max(0, int(round((ctx.now - ctx.invocation.created_at) * 1000.0)))
            remaining_ms = max(0, (ctx.invocation.requested_duration_ms or total_ms) - elapsed_ms)
        else:
            remaining_ms = max(0, int(round((float(deadline_ts) - ctx.now) * 1000.0)))
        remaining_ratio = max(0.0, min(1.0, remaining_ms / float(total_ms)))
        active_leds = max(0, min(ctx.led_count, int(round(remaining_ratio * ctx.led_count))))
        color = _parse_color(params.get("color"), 0xFF9F1A)
        marker_color = _parse_color(params.get("marker_color"), 0xFFF3D1)
        colors: list[int | None] = [None] * ctx.led_count
        for index in range(active_leds):
            colors[index] = color
        if active_leds < ctx.led_count:
            colors[active_leds % ctx.led_count] = marker_color
        return colors


class WarningFlashEffect(BaseEffect):
    definition = EffectDefinition(
        id="warning_flash",
        title="Warning Flash",
        description="Kurzer Warnblitz fuer Event-Layer mit Queue-Semantik.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#FFAA00"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#120400"),
            "period_ms": EffectParamDefinition(name="period_ms", type="duration_ms", default=400, minimum=100, unit="ms"),
            "duty_cycle": EffectParamDefinition(name="duty_cycle", type="float", default=0.5, minimum=0.0, maximum=1.0),
        },
        defaults={"color": "#FFAA00", "background_color": "#120400", "period_ms": 400, "duty_cycle": 0.5},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
            preemptible=False,
        ),
        layer_rules={
            LayerId.EVENT_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
                requires_finite_duration=True,
                queue_mode=QueueMode.PRIORITY_FIFO,
            ),
        },
        tags=("builtin", "event"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        return BlinkColorEffect().render(ctx)