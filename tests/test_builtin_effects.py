from __future__ import annotations

from led_effects.effects.basic import (
    BlinkColorEffect,
    OffEffect,
    ProgressBarEffect,
    SoftPulseEffect,
    SolidColorEffect,
)
from led_effects.effects.overlays import (
    CountdownRingEffect,
    DirectionIndicatorEffect,
    WarningFlashEffect,
)
from src.effect_registry import build_default_effect_registry
from src.effect_schema import (
    EffectInvocation,
    LayerId,
    PlaybackMode,
    QueueMode,
    RenderContext,
)


def make_context(
    effect_class,
    *,
    layer_id: LayerId,
    now: float = 0.0,
    led_count: int = 4,
    params: dict[str, object] | None = None,
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
    )


def test_builtin_registry_exposes_initial_effect_set():
    registry = build_default_effect_registry()

    assert {"off", "solid_color", "soft_pulse", "warning_flash", "progress_bar", "direction_indicator", "countdown_ring"}.issubset(
        set(registry.list_effect_ids())
    )
    assert registry.get("off").effect_class is OffEffect
    assert registry.get("warning_flash").effect_class is WarningFlashEffect


def test_off_effect_renders_black_frame_and_supports_persistent_background_layer():
    effect = OffEffect()
    definition = effect.get_definition()
    frame = effect.render(make_context(OffEffect, layer_id=LayerId.BACKGROUND_STATE_LAYER, led_count=3))

    assert frame == [0, 0, 0]
    assert definition.layer_rules[LayerId.BACKGROUND_STATE_LAYER].persistent_storage is True
    assert definition.layer_rules[LayerId.BACKGROUND_STATE_LAYER].requires_indefinite_duration is True


def test_solid_color_effect_uses_defaults_and_parses_hex_strings():
    effect = SolidColorEffect()
    default_frame = effect.render(make_context(SolidColorEffect, layer_id=LayerId.STATE_LAYER, led_count=2))
    custom_frame = effect.render(
        make_context(
            SolidColorEffect,
            layer_id=LayerId.MAIN_LAYER,
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
        "base_color": "#102030",
        "period_ms": 2000,
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
        "base_color": "#120400",
        "period_ms": 400,
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
            layer_id=LayerId.MAIN_LAYER,
            led_count=6,
            params={"value": 50, "color": "#112233", "base_color": "#010101"},
        )
    )

    assert frame == [0x112233, 0x112233, 0x112233, 0x010101, 0x010101, 0x010101]


def test_direction_indicator_effect_marks_center_and_neighbors_transparently():
    effect = DirectionIndicatorEffect()
    frame = effect.render(
        make_context(
            DirectionIndicatorEffect,
            layer_id=LayerId.ONGOING_OVERLAY_LAYER,
            led_count=12,
            params={"direction_deg": 120.0},
            playback_mode=PlaybackMode.PERSISTENT,
        )
    )

    assert frame[4] == 0xEAF8FF
    assert frame[3] == 0x7FC9FF
    assert frame[5] == 0x7FC9FF
    assert frame[0] is None


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