from __future__ import annotations

from tools.effect_building.standard_effects import discover_standard_effects
from src.engine.effect_registry import build_default_effect_registry
from src.core.effect_schema import (
    EffectInvocation,
    LayerId,
    PlaybackMode,
    QueueMode,
    RenderContext,
)

_EFFECT_CLASSES = {
    spec.effect_id: spec.effect_class
    for spec in discover_standard_effects()
}
CountdownRingEffect = _EFFECT_CLASSES["countdown_ring"]
DirectionIndicatorEffect = _EFFECT_CLASSES["direction_indicator"]
FillRingEffect = _EFFECT_CLASSES["fill_ring"]
ProgressBarEffect = _EFFECT_CLASSES["progress_bar"]
PulsePatternEffect = _EFFECT_CLASSES["pulse_pattern"]
RotatingSegmentEffect = _EFFECT_CLASSES["rotating_segment"]
ShortFlashEffect = _EFFECT_CLASSES["short_flash"]
ShortPingEffect = _EFFECT_CLASSES["short_ping"]
SoftPulseEffect = _EFFECT_CLASSES["soft_pulse"]
SolidColorEffect = _EFFECT_CLASSES["solid_color"]
TimerRingEffect = _EFFECT_CLASSES["timer_ring"]
WarningFlashEffect = _EFFECT_CLASSES["warning_flash"]


def make_context(
    effect_class,
    *,
    layer_id: LayerId,
    now: float = 0.0,
    led_count: int = 4,
    params: dict[str, object] | None = None,
    inputs: dict[str, object] | None = None,
    playback_mode: PlaybackMode | None = None,
    created_at: float = 0.0,
    requested_duration_ms: int | None = None,
) -> RenderContext:
    definition = effect_class.get_definition()
    return RenderContext(
        now=now,
        led_count=led_count,
        layer_id=layer_id,
        definition=definition,
        invocation=EffectInvocation(
            invocation_id=f"inv-{definition.id}",
            effect_id=definition.id,
            target_layer=layer_id,
            playback_mode=playback_mode,
            created_at=created_at,
            requested_duration_ms=requested_duration_ms,
        ),
        params=dict(params or {}),
        inputs=dict(inputs or {}),
    )


def test_builtin_registry_exposes_initial_effect_set():
    registry = build_default_effect_registry()

    assert {
        "solid_color",
        "soft_pulse",
        "warning_flash",
        "progress_bar",
        "direction_indicator",
        "countdown_ring",
        "rotating_segment",
        "fading_rotating_segment",
        "rotating_gradient",
        "chase_dot",
        "soft_pulsing_ring",
        "pulse_pattern",
        "blink_pattern",
        "rotating_gap",
        "radar_sweep",
        "scanner",
        "yin_yang_spin",
        "fill_ring",
        "progress_ring",
        "timer_ring",
        "countdown_segment",
        "highlighted_segment",
        "opposing_markers",
        "short_flash",
        "double_flash",
        "triple_flash",
        "short_pulse",
        "short_soft_pulse",
        "blink_impulse",
        "short_running_dot",
        "short_sweep",
        "sparkle_burst",
        "short_ping",
    }.issubset(set(registry.list_effect_ids()))
    assert registry.get("warning_flash").definition.title == WarningFlashEffect.definition.title


def test_all_new_effects_expose_general_brightness_parameter():
    registry = build_default_effect_registry()
    effect_ids = {
        "rotating_segment",
        "fading_rotating_segment",
        "rotating_gradient",
        "chase_dot",
        "soft_pulsing_ring",
        "pulse_pattern",
        "blink_pattern",
        "rotating_gap",
        "radar_sweep",
        "scanner",
        "yin_yang_spin",
        "fill_ring",
        "progress_ring",
        "timer_ring",
        "countdown_segment",
        "highlighted_segment",
        "opposing_markers",
        "short_flash",
        "double_flash",
        "triple_flash",
        "short_pulse",
        "short_soft_pulse",
        "blink_impulse",
        "short_running_dot",
        "short_sweep",
        "sparkle_burst",
        "short_ping",
    }

    for effect_id in effect_ids:
        definition = registry.get(effect_id).definition
        assert "brightness" in definition.parameter_schema
        assert definition.defaults["brightness"] == 1.0


def test_builtin_registry_uses_final_public_parameter_names():
    registry = build_default_effect_registry()

    assert "background_color" in registry.get("soft_pulse").definition.parameter_schema
    assert "base_color" not in registry.get("soft_pulse").definition.parameter_schema
    assert "direction_deg" in registry.get("direction_indicator").definition.runtime_input_schema
    assert registry.get("direction_indicator").definition.runtime_input_schema[
        "direction_deg"
    ].aliases == ("direction",)
    assert "direction_deg" not in registry.get("direction_indicator").definition.parameter_schema


def test_solid_color_effect_uses_defaults_and_parses_hex_strings():
    effect = SolidColorEffect()
    default_frame = effect.render(make_context(SolidColorEffect, layer_id=LayerId.STATE_LAYER, led_count=2))
    custom_frame = effect.render(
        make_context(
            SolidColorEffect,
            layer_id=LayerId.STATE_LAYER,
            led_count=2,
            params={"color": "0x224466"},
        )
    )

    assert default_frame == [0x33AAFF, 0x33AAFF]
    assert custom_frame == [0x224466, 0x224466]


def test_soft_pulse_effect_reaches_base_and_accent_color_at_deterministic_times():
    effect = SoftPulseEffect()
    definition = effect.get_definition()
    params = {
        "color": "#204060",
        "background_color": "#102030",
        "speed": 0.9,
    }
    start_frame = effect.render(
        make_context(
            SoftPulseEffect,
            layer_id=LayerId.BACKGROUND_STATE_LAYER,
            now=0.0,
            led_count=2,
            params=params,
            playback_mode=PlaybackMode.PERSISTENT,
        )
    )
    peak_frame = effect.render(
        make_context(
            SoftPulseEffect,
            layer_id=LayerId.BACKGROUND_STATE_LAYER,
            now=1.0,
            led_count=2,
            params=params,
            playback_mode=PlaybackMode.PERSISTENT,
        )
    )

    assert start_frame == [0x102030, 0x102030]
    assert peak_frame == [0x204060, 0x204060]
    assert definition.layer_rules[LayerId.BACKGROUND_STATE_LAYER].persistent_storage is True
    assert definition.layer_rules[LayerId.STATE_LAYER].allowed_playback_modes == (
        PlaybackMode.LOOP,
        PlaybackMode.PERSISTENT,
    )


def test_warning_flash_effect_is_event_only_and_uses_priority_fifo_queueing():
    effect = WarningFlashEffect()
    definition = effect.get_definition()
    params = {
        "color": "#FFAA00",
        "background_color": "#120400",
        "speed": 1.0,
        "duty_cycle": 0.5,
    }
    on_frame = effect.render(
        make_context(
            WarningFlashEffect,
            layer_id=LayerId.EVENT_LAYER,
            now=0.0,
            led_count=3,
            params=params,
            playback_mode=PlaybackMode.SINGLE_RUN,
        )
    )
    off_frame = effect.render(
        make_context(
            WarningFlashEffect,
            layer_id=LayerId.EVENT_LAYER,
            now=0.3,
            led_count=3,
            params=params,
            playback_mode=PlaybackMode.SINGLE_RUN,
        )
    )

    assert on_frame == [0xFFAA00, 0xFFAA00, 0xFFAA00]
    assert off_frame == [0x120400, 0x120400, 0x120400]
    assert tuple(definition.layer_rules) == (LayerId.EVENT_LAYER,)
    assert definition.layer_rules[LayerId.EVENT_LAYER].queue_mode is QueueMode.PRIORITY_FIFO
    assert definition.layer_rules[LayerId.EVENT_LAYER].requires_finite_duration is True
    assert definition.capabilities.supports_queueing is True
    assert definition.capabilities.preemptible is False


def test_progress_bar_effect_renders_expected_led_split():
    effect = ProgressBarEffect()
    frame = effect.render(
        make_context(
            ProgressBarEffect,
            layer_id=LayerId.ONGOING_OVERLAY_LAYER,
            led_count=6,
            params={"color": "#112233", "background_color": "#010101"},
            inputs={"progress": 50},
        )
    )

    assert frame == [0x112233, 0x112233, 0x112233, 0x010101, 0x010101, 0x010101]


def test_direction_indicator_effect_marks_one_led_transparently():
    effect = DirectionIndicatorEffect()
    frame = effect.render(
        make_context(
            DirectionIndicatorEffect,
            layer_id=LayerId.ONGOING_OVERLAY_LAYER,
            led_count=12,
            inputs={"direction_deg": 120.0, "detection_state": "sound"},
            playback_mode=PlaybackMode.PERSISTENT,
        )
    )

    assert frame[4] == 0x00C066
    assert sum(value is not None for value in frame) == 1


def test_countdown_ring_effect_uses_deadline_and_duration_to_render_remaining_segment():
    effect = CountdownRingEffect()
    frame = effect.render(
        make_context(
            CountdownRingEffect,
            layer_id=LayerId.TEMP_OVERLAY_LAYER,
            now=0.5,
            led_count=6,
            params={"total_ms": 4000, "deadline_ts": 2.0},
            playback_mode=PlaybackMode.SINGLE_RUN,
            created_at=0.0,
            requested_duration_ms=2000,
        )
    )

    assert frame[:2] == [0xFF9F1A, 0xFF9F1A]
    assert frame[2] == 0xFFF3D1
    assert frame[3:] == [None, None, None]


def test_rotating_segment_effect_moves_a_fixed_length_segment():
    effect = RotatingSegmentEffect()
    frame = effect.render(
        make_context(
            RotatingSegmentEffect,
            layer_id=LayerId.STATE_LAYER,
            now=0.5,
            led_count=8,
            params={"speed": 2.0, "segment_length": 3, "color": "#112233", "background_color": "#000000"},
            playback_mode=PlaybackMode.PERSISTENT,
        )
    )

    assert frame == [0x000000, 0x000000, 0x000000, 0x000000, 0x112233, 0x112233, 0x112233, 0x000000]


def test_general_brightness_scales_foreground_without_altering_background():
    effect = RotatingSegmentEffect()
    frame = effect.render(
        make_context(
            RotatingSegmentEffect,
            layer_id=LayerId.STATE_LAYER,
            led_count=6,
            params={
                "speed": 0.0,
                "segment_length": 2,
                "color": "#204060",
                "background_color": "#010203",
                "brightness": 0.5,
            },
            playback_mode=PlaybackMode.PERSISTENT,
        )
    )

    assert frame == [0x102030, 0x102030, 0x010203, 0x010203, 0x010203, 0x010203]


def test_pulse_pattern_effect_supports_double_pulse_behavior():
    effect = PulsePatternEffect()
    bright_frame = effect.render(
        make_context(
            PulsePatternEffect,
            layer_id=LayerId.STATE_LAYER,
            now=0.15,
            led_count=4,
            params={"pattern": "double", "speed": 1.0, "color": "#224466", "background_color": "#000000"},
            playback_mode=PlaybackMode.PERSISTENT,
        )
    )
    dark_frame = effect.render(
        make_context(
            PulsePatternEffect,
            layer_id=LayerId.STATE_LAYER,
            now=0.8,
            led_count=4,
            params={"pattern": "double", "speed": 1.0, "color": "#224466", "background_color": "#000000"},
            playback_mode=PlaybackMode.PERSISTENT,
        )
    )

    assert any(pixel != 0x000000 for pixel in bright_frame)
    assert dark_frame == [0x000000, 0x000000, 0x000000, 0x000000]


def test_fill_ring_respects_start_led_and_direction():
    effect = FillRingEffect()
    frame = effect.render(
        make_context(
            FillRingEffect,
            layer_id=LayerId.ONGOING_OVERLAY_LAYER,
            led_count=8,
            params={
                "color": "#ABCDEF",
                "background_color": "#010101",
                "start_led": 6,
                "reverse": True,
            },
            inputs={"progress": 50},
            playback_mode=PlaybackMode.PERSISTENT,
        )
    )

    assert frame == [0x010101, 0x010101, 0x010101, 0xABCDEF, 0xABCDEF, 0xABCDEF, 0xABCDEF, 0x010101]


def test_timer_ring_uses_remaining_ratio_for_colored_leds():
    effect = TimerRingEffect()
    frame = effect.render(
        make_context(
            TimerRingEffect,
            layer_id=LayerId.TEMP_OVERLAY_LAYER,
            now=0.5,
            led_count=8,
            params={"total_ms": 4000, "deadline_ts": 2.0, "color": "#FF0000", "background_color": "#000011"},
            playback_mode=PlaybackMode.SINGLE_RUN,
            created_at=0.0,
            requested_duration_ms=2000,
        )
    )

    assert frame[:3] == [0xFF0000, 0xFF0000, 0xFF0000]
    assert frame[3:] == [0x000011, 0x000011, 0x000011, 0x000011, 0x000011]


def test_direction_indicator_is_pull_driven_and_transparent_without_activity():
    registry = build_default_effect_registry()

    registered = registry.get("direction_indicator")
    definition = registered.definition
    assert definition.input_sampling.mode.value == "pull"
    assert definition.input_sampling.provider_id == "respeaker_doa"
    assert definition.input_sampling.interval_ms == 0
    frame = registered.effect_class().render(
        make_context(
            registered.effect_class,
            layer_id=LayerId.ONGOING_OVERLAY_LAYER,
            led_count=12,
            inputs={"direction_deg": 120.0, "detection_state": "none"},
            playback_mode=PlaybackMode.PERSISTENT,
        )
    )

    assert frame == [None] * 12


def test_short_ping_renders_a_head_and_fading_trail_from_start_led():
    effect = ShortPingEffect()
    frame = effect.render(
        make_context(
            ShortPingEffect,
            layer_id=LayerId.EVENT_LAYER,
            now=0.35,
            led_count=8,
            params={"start_led": 2, "reverse": False, "color": "#3366FF", "background_color": "#000000"},
            playback_mode=PlaybackMode.SINGLE_RUN,
            created_at=0.0,
            requested_duration_ms=700,
        )
    )

    assert frame[5] == 0x3366FF
    assert frame[4] != 0x000000
    assert frame[3] != 0x000000


def test_general_brightness_also_applies_to_event_effects():
    effect = ShortFlashEffect()
    on_frame = effect.render(
        make_context(
            ShortFlashEffect,
            layer_id=LayerId.EVENT_LAYER,
            now=0.05,
            led_count=4,
            params={"color": "#204060", "background_color": "#010203", "brightness": 0.5},
            playback_mode=PlaybackMode.SINGLE_RUN,
            created_at=0.0,
            requested_duration_ms=250,
        )
    )
    off_frame = effect.render(
        make_context(
            ShortFlashEffect,
            layer_id=LayerId.EVENT_LAYER,
            now=0.4,
            led_count=4,
            params={"color": "#204060", "background_color": "#010203", "brightness": 0.5},
            playback_mode=PlaybackMode.SINGLE_RUN,
            created_at=0.0,
            requested_duration_ms=250,
        )
    )

    assert on_frame == [0x102030, 0x102030, 0x102030, 0x102030]
    assert off_frame == [0x010203, 0x010203, 0x010203, 0x010203]
