from __future__ import annotations

from src.color_math import blend, scale_color
from src.effect_schema import (
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

from led_effects.effects.common import (
    _merge_params,
    _parse_color,
    _parse_float,
    _parse_int,
    _persistent_state_rules,
    _pulse_mix,
)


class OffEffect(BaseEffect):
    definition = EffectDefinition(
        id="off",
        title="Off",
        description="Schaltet alle LEDs des Ziel-Layers aus.",
        defaults={},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_persistent_state_rules(),
        tags=("builtin", "state", "fallback"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        return [0] * ctx.led_count


class SolidColorEffect(BaseEffect):
    definition = EffectDefinition(
        id="solid_color",
        title="Solid Color",
        description="Faerbt den gesamten Ziel-Layer statisch ein.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "brightness": EffectParamDefinition(name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0),
        },
        defaults={"color": "#33AAFF", "brightness": 1.0},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules={
            **_persistent_state_rules(),
            LayerId.TEMP_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
                requires_finite_duration=True,
            ),
            LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                requires_indefinite_duration=True,
            ),
        },
        tags=("builtin", "state"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        color = _parse_color(params.get("color"), 0)
        brightness = min(1.0, max(0.0, _parse_float(params.get("brightness"), 1.0)))
        color = scale_color(color, brightness)
        return [color] * ctx.led_count


class SoftPulseEffect(BaseEffect):
    definition = EffectDefinition(
        id="soft_pulse",
        title="Soft Pulse",
        description="Weiches Pulsieren zwischen Grund- und Akzentfarbe.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "base_color": EffectParamDefinition(name="base_color", type="color", default="#050A0F"),
            "period_ms": EffectParamDefinition(
                name="period_ms",
                type="duration_ms",
                default=1800,
                minimum=100,
                unit="ms",
            ),
        },
        defaults={
            "color": "#33AAFF",
            "base_color": "#050A0F",
            "period_ms": 1800,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_persistent_state_rules(),
        tags=("builtin", "state", "animated"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        color = _parse_color(params.get("color"), 0x33AAFF)
        base_color = _parse_color(params.get("base_color"), 0x050A0F)
        period_ms = max(100, _parse_int(params.get("period_ms"), 1800))
        pulsed_color = blend(base_color, color, _pulse_mix(ctx.now, period_ms))
        return [pulsed_color] * ctx.led_count


class BlinkColorEffect(BaseEffect):
    definition = EffectDefinition(
        id="blink_color",
        title="Blink Color",
        description="Blinkt zwischen Akzent- und Grundfarbe.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#FFAA00"),
            "base_color": EffectParamDefinition(name="base_color", type="color", default="#000000"),
            "period_ms": EffectParamDefinition(name="period_ms", type="duration_ms", default=900, minimum=100, unit="ms"),
            "duty_cycle": EffectParamDefinition(name="duty_cycle", type="float", default=0.5, minimum=0.0, maximum=1.0),
        },
        defaults={"color": "#FFAA00", "base_color": "#000000", "period_ms": 900, "duty_cycle": 0.5},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_queueing=True,
            restorable=True,
        ),
        layer_rules={
            LayerId.STATE_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                requires_indefinite_duration=True,
            ),
            LayerId.MAIN_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            ),
            LayerId.TEMP_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
                requires_finite_duration=True,
            ),
            LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                requires_indefinite_duration=True,
            ),
            LayerId.EVENT_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
                requires_finite_duration=True,
                queue_mode=QueueMode.PRIORITY_FIFO,
            ),
        },
        tags=("builtin", "animated"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        color = _parse_color(params.get("color"), 0xFFAA00)
        base_color = _parse_color(params.get("base_color"), 0x000000)
        period_ms = max(100, _parse_int(params.get("period_ms"), 900))
        duty_cycle = min(1.0, max(0.0, _parse_float(params.get("duty_cycle"), 0.5)))
        phase = ((ctx.now * 1000.0) % period_ms) / float(period_ms)
        frame_color = color if phase < duty_cycle else base_color
        return [frame_color] * ctx.led_count


class ProgressBarEffect(BaseEffect):
    definition = EffectDefinition(
        id="progress_bar",
        title="Progress Bar",
        description="Bildet einen Fortschritt ringfoermig als normale Effektklasse ab.",
        parameter_schema={
            "value": EffectParamDefinition(name="value", type="float", default=0.0, minimum=0.0, maximum=100.0),
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "base_color": EffectParamDefinition(name="base_color", type="color", default="#050505"),
        },
        defaults={"value": 0.0, "color": "#33AAFF", "base_color": "#050505"},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules={
            LayerId.MAIN_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            ),
            LayerId.TEMP_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
                requires_finite_duration=True,
            ),
        },
        tags=("builtin", "progress"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        value = min(100.0, max(0.0, _parse_float(params.get("value"), 0.0)))
        active_leds = int(round((value / 100.0) * ctx.led_count))
        color = _parse_color(params.get("color"), 0x33AAFF)
        base_color = _parse_color(params.get("base_color"), 0x050505)
        return [color if index < active_leds else base_color for index in range(ctx.led_count)]