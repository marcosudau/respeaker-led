"""Comprehensive tests for the advanced per-LED effects."""
from __future__ import annotations

import threading
import time

import pytest

from led_effects.effects_engine import (
    RGB,
    Colors,
    LED_COUNT,
    RecordingBackend,
    EffectContext,
    CustomDoaEffect,
    TimerCountdownEffect,
    ProgressRingEffect,
    SpinnerEffect,
    PulseWaveEffect,
    SegmentMeterEffect,
    parse_effect_spec,
    build_standard_effects,
)


# ============================================================
# Helpers
# ============================================================

def make_ctx(backend: RecordingBackend | None = None) -> EffectContext:
    return EffectContext(
        backend=backend or RecordingBackend(),
        stop_event=threading.Event(),
    )


def run_timed(effect, ctx: EffectContext, duration: float = 0.15):
    """Run an effect in a thread, stop after *duration* seconds."""
    t = threading.Thread(target=effect.run, args=(ctx,))
    t.start()
    time.sleep(duration)
    ctx.stop_event.set()
    t.join(timeout=2.0)
    assert not t.is_alive(), "Effect thread did not stop"


def get_ring_calls(backend: RecordingBackend) -> list[list[RGB]]:
    """Extract all set_ring_colors call arguments."""
    return [c.args[0] for c in backend.calls if c.method == "set_ring_colors"]


# ============================================================
# CustomDoaEffect
# ============================================================


class TestCustomDoaEffect:
    def test_static_direction_north(self):
        """Direction 0° → LED index 0 is center with wings at 11 and 1."""
        ctx = make_ctx()
        effect = CustomDoaEffect(
            direction_deg=0.0,
            center_color=Colors.CYAN,
            wing_color=Colors.BLUE,
            base_color=Colors.BLACK,
        )
        run_timed(effect, ctx, 0.08)
        rings = get_ring_calls(ctx.backend)
        assert len(rings) > 0
        ring = rings[0]
        assert len(ring) == LED_COUNT
        assert ring[0] == Colors.CYAN       # center
        assert ring[1] == Colors.BLUE        # right wing
        assert ring[11] == Colors.BLUE       # left wing
        # all others are base
        for i in range(2, 11):
            assert ring[i] == Colors.BLACK

    def test_static_direction_180(self):
        """Direction 180° → LED index 6."""
        ctx = make_ctx()
        effect = CustomDoaEffect(direction_deg=180.0)
        run_timed(effect, ctx, 0.08)
        rings = get_ring_calls(ctx.backend)
        ring = rings[0]
        assert ring[6] == effect.center_color

    def test_direction_provider(self):
        """Live direction provider updates the ring."""
        directions = iter([0.0, 90.0, 180.0, 270.0])
        current = [0.0]

        def provider():
            try:
                current[0] = next(directions)
            except StopIteration:
                pass
            return current[0]

        ctx = make_ctx()
        effect = CustomDoaEffect(
            direction_provider=provider,
            refresh_interval=0.02,
        )
        run_timed(effect, ctx, 0.15)
        rings = get_ring_calls(ctx.backend)
        # multiple frames should have been rendered
        assert len(rings) >= 3

    def test_wrapping_at_360(self):
        """360° wraps to LED 0."""
        ctx = make_ctx()
        effect = CustomDoaEffect(direction_deg=360.0)
        run_timed(effect, ctx, 0.06)
        ring = get_ring_calls(ctx.backend)[0]
        assert ring[0] == effect.center_color

    def test_stops_cooperatively(self):
        ctx = make_ctx()
        ctx.stop_event.set()  # pre-stopped
        effect = CustomDoaEffect()
        effect.run(ctx)  # should return immediately


# ============================================================
# TimerCountdownEffect
# ============================================================


class TestTimerCountdownEffect:
    def test_basic_countdown(self):
        """Timer runs and produces ring updates."""
        ctx = make_ctx()
        effect = TimerCountdownEffect(
            total_seconds=0.3,
            brightness_steps=2,
            tick_flash=False,
        )
        t = threading.Thread(target=effect.run, args=(ctx,))
        t.start()
        t.join(timeout=3.0)
        assert not t.is_alive()
        rings = get_ring_calls(ctx.backend)
        assert len(rings) > 0

    def test_countdown_ends_dark(self):
        """After countdown finishes, the ring should go dark."""
        backend = RecordingBackend()
        ctx = EffectContext(backend=backend, stop_event=threading.Event())
        effect = TimerCountdownEffect(
            total_seconds=0.2,
            brightness_steps=2,
            tick_flash=False,
        )
        effect.run(ctx)
        rings = get_ring_calls(backend)
        last_ring = rings[-1]
        assert all(c == effect.background for c in last_ring)

    def test_led_urgency_colors(self):
        """The last LEDs should get warn/critical colors."""
        effect = TimerCountdownEffect(brightness_steps=1)
        # Build ring with all LEDs fully lit
        ring = effect._build_ring(LED_COUNT * 1, 1)
        # Index 11 (last) → critical
        assert ring[11] == effect.critical_color
        # Index 10 → warn
        assert ring[10] == effect.warn_color
        # Index 0 → normal color
        assert ring[0] == effect.color

    def test_tick_flash(self):
        """Tick flash produces white LED frames."""
        ctx = make_ctx()
        effect = TimerCountdownEffect(
            total_seconds=0.3,
            brightness_steps=2,
            tick_flash=True,
        )
        t = threading.Thread(target=effect.run, args=(ctx,))
        t.start()
        t.join(timeout=3.0)
        rings = get_ring_calls(ctx.backend)
        # At least one ring should contain a white LED (flash)
        has_white = any(
            any(c == Colors.WHITE for c in ring) for ring in rings
        )
        assert has_white

    def test_stops_early(self):
        ctx = make_ctx()
        ctx.stop_event.set()
        effect = TimerCountdownEffect(total_seconds=60.0)
        effect.run(ctx)  # should exit immediately


# ============================================================
# ProgressRingEffect
# ============================================================


class TestProgressRingEffect:
    def test_zero_progress(self):
        effect = ProgressRingEffect()
        ring = effect._build_ring(0.0)
        assert all(c == effect.background for c in ring)

    def test_full_progress(self):
        effect = ProgressRingEffect()
        ring = effect._build_ring(1.0)
        assert all(c == effect.color for c in ring)

    def test_half_progress(self):
        effect = ProgressRingEffect(brightness_steps=1)
        ring = effect._build_ring(0.5)
        filled = sum(1 for c in ring if c == effect.color)
        assert filled == 6

    def test_sub_led_brightness(self):
        """Partial fill produces intermediate brightness."""
        effect = ProgressRingEffect(
            color=RGB(100, 100, 100),
            background=Colors.BLACK,
            brightness_steps=4,
        )
        # 1 LED = 4 steps, 1 step filled = 25% brightness on LED 0
        ring = effect._build_ring(1 / (LED_COUNT * 4))
        # LED 0 should be partially lit (not full and not background)
        assert ring[0] != effect.color
        assert ring[0] != effect.background

    def test_tip_color(self):
        """Tip highlight appears on leading edge."""
        effect = ProgressRingEffect(
            tip_color=Colors.WHITE,
            brightness_steps=1,
        )
        ring = effect._build_ring(0.5)
        assert Colors.WHITE in ring

    def test_counter_clockwise(self):
        """Counter-clockwise fills from the other end."""
        effect = ProgressRingEffect(
            clockwise=False,
            brightness_steps=1,
            color=Colors.RED,
            background=Colors.BLACK,
        )
        ring = effect._build_ring(1 / LED_COUNT)
        # In counter-clockwise, first filled LED at index 11
        assert ring[LED_COUNT - 1] == Colors.RED

    def test_live_provider(self):
        """Progress updates via provider callback."""
        values = [0.0, 0.5, 1.0]
        idx = [0]

        def provider():
            v = values[min(idx[0], len(values) - 1)]
            idx[0] += 1
            return v

        ctx = make_ctx()
        effect = ProgressRingEffect(
            progress_provider=provider,
            refresh_interval=0.02,
        )
        run_timed(effect, ctx, 0.1)
        rings = get_ring_calls(ctx.backend)
        assert len(rings) >= 2


# ============================================================
# SpinnerEffect
# ============================================================


class TestSpinnerEffect:
    def test_produces_frames(self):
        ctx = make_ctx()
        effect = SpinnerEffect(period=0.2)
        run_timed(effect, ctx, 0.1)
        rings = get_ring_calls(ctx.backend)
        assert len(rings) > 0

    def test_dot_visible(self):
        """At least one LED should have the dot color."""
        ctx = make_ctx()
        effect = SpinnerEffect(color=Colors.RED, background=Colors.BLACK)
        run_timed(effect, ctx, 0.08)
        ring = get_ring_calls(ctx.backend)[0]
        assert Colors.RED in ring

    def test_dual_dots(self):
        """Two dots should both be visible."""
        ctx = make_ctx()
        effect = SpinnerEffect(
            color=Colors.RED,
            background=Colors.BLACK,
            dot_count=2,
            tail_length=0,
        )
        run_timed(effect, ctx, 0.08)
        ring = get_ring_calls(ctx.backend)[0]
        red_count = sum(1 for c in ring if c == Colors.RED)
        assert red_count == 2

    def test_tail_creates_gradient(self):
        """Tail LEDs should be intermediate brightness."""
        ctx = make_ctx()
        effect = SpinnerEffect(
            color=Colors.WHITE,
            background=Colors.BLACK,
            tail_length=3,
        )
        run_timed(effect, ctx, 0.08)
        ring = get_ring_calls(ctx.backend)[0]
        # There should be LEDs that are neither white nor black (tail gradient)
        non_extremes = [c for c in ring if c != Colors.WHITE and c != Colors.BLACK]
        assert len(non_extremes) > 0

    def test_counter_clockwise(self):
        ctx = make_ctx()
        effect = SpinnerEffect(clockwise=False, period=0.2)
        run_timed(effect, ctx, 0.08)
        assert len(get_ring_calls(ctx.backend)) > 0


# ============================================================
# PulseWaveEffect
# ============================================================


class TestPulseWaveEffect:
    def test_produces_frames(self):
        ctx = make_ctx()
        effect = PulseWaveEffect(period=0.3)
        run_timed(effect, ctx, 0.1)
        rings = get_ring_calls(ctx.backend)
        assert len(rings) > 0

    def test_gaussian_gradient(self):
        """Ring should have brightness gradient (not all same color)."""
        ctx = make_ctx()
        effect = PulseWaveEffect(
            color=RGB(200, 200, 200),
            background=Colors.BLACK,
            width=2.0,
        )
        run_timed(effect, ctx, 0.08)
        ring = get_ring_calls(ctx.backend)[0]
        unique_colors = set(ring)
        # Gaussian over 12 LEDs with width=2 → multiple distinct brightnesses
        assert len(unique_colors) > 3

    def test_min_brightness(self):
        """All LEDs should have at least min_brightness fraction."""
        ctx = make_ctx()
        effect = PulseWaveEffect(
            color=RGB(100, 100, 100),
            background=Colors.BLACK,
            min_brightness=0.5,
        )
        run_timed(effect, ctx, 0.05)
        ring = get_ring_calls(ctx.backend)[0]
        for c in ring:
            # At min_brightness=0.5, minimum channel should be ~50
            assert c.r >= 45  # small tolerance for rounding


# ============================================================
# SegmentMeterEffect
# ============================================================


class TestSegmentMeterEffect:
    def test_zero_level(self):
        effect = SegmentMeterEffect()
        ring = effect._build_ring(0.0)
        assert all(c == effect.background for c in ring)

    def test_full_level(self):
        effect = SegmentMeterEffect()
        ring = effect._build_ring(1.0)
        assert all(c != effect.background for c in ring)

    def test_color_zones(self):
        """Full level should show all three zone colors."""
        effect = SegmentMeterEffect(
            low_color=Colors.GREEN,
            mid_color=Colors.YELLOW,
            high_color=Colors.RED,
        )
        ring = effect._build_ring(1.0)
        assert Colors.GREEN in ring
        assert Colors.YELLOW in ring
        assert Colors.RED in ring

    def test_partial_fill(self):
        effect = SegmentMeterEffect()
        ring = effect._build_ring(0.5)
        active = sum(1 for c in ring if c != effect.background)
        assert active == 6

    def test_live_provider(self):
        ctx = make_ctx()
        effect = SegmentMeterEffect(
            level_provider=lambda: 0.75,
            refresh_interval=0.02,
        )
        run_timed(effect, ctx, 0.08)
        rings = get_ring_calls(ctx.backend)
        assert len(rings) > 0


# ============================================================
# Config loader integration
# ============================================================


class TestAdvancedConfigLoader:
    def test_custom_doa_from_spec(self):
        spec = {
            "type": "custom_doa",
            "direction_deg": 90,
            "center_color": "cyan",
            "wing_color": "#0000FF",
            "base_color": [0, 0, 0],
        }
        effect = parse_effect_spec(spec)
        assert isinstance(effect, CustomDoaEffect)
        assert effect.direction_deg == 90.0
        assert effect.center_color == Colors.CYAN

    def test_timer_from_spec(self):
        spec = {
            "type": "timer",
            "total_seconds": 30,
            "color": "green",
            "tick_flash": False,
        }
        effect = parse_effect_spec(spec)
        assert isinstance(effect, TimerCountdownEffect)
        assert effect.total_seconds == 30.0
        assert effect.tick_flash is False

    def test_progress_from_spec(self):
        spec = {
            "type": "progress",
            "color": "blue",
            "clockwise": False,
        }
        effect = parse_effect_spec(spec)
        assert isinstance(effect, ProgressRingEffect)
        assert effect.clockwise is False

    def test_spinner_from_spec(self):
        spec = {
            "type": "spinner",
            "color": "red",
            "dot_count": 3,
            "period": 2.0,
        }
        effect = parse_effect_spec(spec)
        assert isinstance(effect, SpinnerEffect)
        assert effect.dot_count == 3
        assert effect.period == 2.0

    def test_pulse_wave_from_spec(self):
        spec = {"type": "pulse_wave", "color": "cyan", "width": 4.0}
        effect = parse_effect_spec(spec)
        assert isinstance(effect, PulseWaveEffect)
        assert effect.width == 4.0

    def test_segment_meter_from_spec(self):
        spec = {
            "type": "segment_meter",
            "low_color": "green",
            "high_color": "red",
        }
        effect = parse_effect_spec(spec)
        assert isinstance(effect, SegmentMeterEffect)
        assert effect.low_color == Colors.GREEN


# ============================================================
# Standard library integration
# ============================================================


class TestAdvancedStdlib:
    def test_stdlib_has_advanced_effects(self):
        effects = build_standard_effects()
        expected = [
            "state_spinner",
            "state_dual_spinner",
            "state_pulse_wave",
            "state_custom_doa",
            "event_timer_10s",
            "event_timer_30s",
            "event_timer_60s",
        ]
        for name in expected:
            assert name in effects, f"Missing stdlib entry: {name}"

    def test_spinner_preset_runs(self):
        effects = build_standard_effects()
        ctx = make_ctx()
        run_timed(effects["state_spinner"], ctx, 0.08)
        assert len(get_ring_calls(ctx.backend)) > 0

    def test_timer_preset_runs(self):
        effects = build_standard_effects()
        ctx = make_ctx()
        run_timed(effects["event_timer_10s"], ctx, 0.1)
        assert len(get_ring_calls(ctx.backend)) > 0


# ============================================================
# Backend set_ring_colors
# ============================================================


class TestBackendSetRingColors:
    def test_recording_backend(self):
        backend = RecordingBackend()
        colors = [Colors.RED] * LED_COUNT
        backend.set_ring_colors(colors)
        assert len(backend.calls) == 1
        assert backend.calls[0].method == "set_ring_colors"
        assert backend.calls[0].args[0] == colors

    def test_dryrun_backend_no_crash(self):
        from led_effects.effects_engine import DryRunBackend
        backend = DryRunBackend()
        backend.set_ring_colors([Colors.BLACK] * LED_COUNT)


# ============================================================
# Edge cases: _deg_to_led_index
# ============================================================


class TestDegToLedIndex:
    def test_zero(self):
        from led_effects.effects_engine.advanced_effects import _deg_to_led_index
        assert _deg_to_led_index(0) == 0

    def test_360(self):
        from led_effects.effects_engine.advanced_effects import _deg_to_led_index
        assert _deg_to_led_index(360) == 0

    def test_90(self):
        from led_effects.effects_engine.advanced_effects import _deg_to_led_index
        assert _deg_to_led_index(90) == 3

    def test_180(self):
        from led_effects.effects_engine.advanced_effects import _deg_to_led_index
        assert _deg_to_led_index(180) == 6

    def test_270(self):
        from led_effects.effects_engine.advanced_effects import _deg_to_led_index
        assert _deg_to_led_index(270) == 9

    def test_negative(self):
        from led_effects.effects_engine.advanced_effects import _deg_to_led_index
        assert _deg_to_led_index(-90) == 9  # same as 270
