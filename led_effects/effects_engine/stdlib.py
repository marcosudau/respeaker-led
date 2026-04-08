"""Standard effect library – ready-made sets for common use cases."""
from __future__ import annotations

from .advanced_effects import (
    CustomDoaEffect,
    PulseWaveEffect,
    SpinnerEffect,
    TimerCountdownEffect,
)
from .effects import (
    AlternateColorEffect,
    BlinkEffect,
    BreathEffect,
    DoaEffect,
    LedEffect,
    OffEffect,
    RainbowEffect,
    SequenceEffect,
    StaticColorEffect,
)
from .registry import EffectRegistry
from .rgb import Colors, RGB


def build_standard_effects() -> dict[str, LedEffect]:
    """Return the full standard effect library as a plain dict.

    Semantic groups:
    - ``state_*``  – long-running / looping status indicators
    - ``event_*``  – short one-shot notifications
    - ``system_*`` – boot / shutdown sequences
    """
    return {
        # ---- States (looping / persistent) ----------------------
        "state_idle": BreathEffect(
            color=Colors.SOFT_GREEN,
            speed=1,
            brightness=60,
            persistent=True,
        ),
        "state_waiting": BlinkEffect(
            color=Colors.SOFT_YELLOW,
            on_seconds=0.12,
            off_seconds=1.20,
        ),
        "state_processing": RainbowEffect(
            speed=2,
            brightness=90,
            persistent=True,
        ),
        "state_connecting": AlternateColorEffect(
            colors=[Colors.SOFT_BLUE, Colors.SOFT_CYAN],
            interval_seconds=0.35,
        ),
        "state_offline": BlinkEffect(
            color=Colors.SOFT_RED,
            on_seconds=0.25,
            off_seconds=1.00,
        ),
        "state_muted": StaticColorEffect(
            color=Colors.RED,
            persistent=True,
        ),
        "state_listening": BreathEffect(
            color=Colors.CYAN,
            speed=1,
            brightness=90,
            persistent=True,
        ),
        "state_thinking": AlternateColorEffect(
            colors=[Colors.SOFT_BLUE, Colors.SOFT_PURPLE],
            interval_seconds=0.25,
        ),
        "state_speaking": BlinkEffect(
            color=Colors.BLUE,
            on_seconds=0.10,
            off_seconds=0.10,
        ),
        "state_doa": DoaEffect(
            base_color=Colors.SOFT_BLUE,
            doa_color=Colors.YELLOW,
            persistent=True,
        ),

        # ---- Events (one-shot) ----------------------------------
        "event_success": BlinkEffect(
            color=Colors.GREEN,
            on_seconds=0.12,
            off_seconds=0.06,
            repeat=2,
        ),
        "event_warning": BlinkEffect(
            color=Colors.YELLOW,
            on_seconds=0.18,
            off_seconds=0.10,
            repeat=2,
        ),
        "event_error": BlinkEffect(
            color=Colors.RED,
            on_seconds=0.12,
            off_seconds=0.08,
            repeat=3,
        ),
        "event_notification": SequenceEffect(
            effects=[
                StaticColorEffect(Colors.WHITE, hold_seconds=0.06),
                OffEffect(hold_seconds=0.04),
                StaticColorEffect(Colors.PURPLE, hold_seconds=0.16),
                OffEffect(hold_seconds=0.04),
            ],
            repeat=1,
        ),
        "event_connected": BlinkEffect(
            color=Colors.GREEN,
            on_seconds=0.08,
            off_seconds=0.05,
            repeat=2,
        ),
        "event_disconnected": BlinkEffect(
            color=Colors.RED,
            on_seconds=0.08,
            off_seconds=0.05,
            repeat=2,
        ),
        "event_ack": BlinkEffect(
            color=Colors.CYAN,
            on_seconds=0.08,
            off_seconds=0.04,
            repeat=1,
        ),

        # ---- System (one-shot sequences) ------------------------
        "system_boot": SequenceEffect(
            effects=[
                RainbowEffect(speed=1, brightness=160, hold_seconds=1.2),
                StaticColorEffect(Colors.WHITE, hold_seconds=0.10),
                BreathEffect(
                    Colors.SOFT_BLUE, speed=1, brightness=80, hold_seconds=0.6
                ),
                OffEffect(hold_seconds=0.05),
            ],
            repeat=1,
        ),
        "system_shutdown": SequenceEffect(
            effects=[
                StaticColorEffect(Colors.ORANGE, hold_seconds=0.20),
                StaticColorEffect(Colors.RED, hold_seconds=0.20),
                OffEffect(),
            ],
            repeat=1,
        ),

        # ---- Advanced states (per-LED ring control) -------------
        "state_spinner": SpinnerEffect(
            color=Colors.CYAN,
            tail_color=Colors.SOFT_BLUE,
            dot_count=1,
            tail_length=3,
            period=1.0,
        ),
        "state_dual_spinner": SpinnerEffect(
            color=Colors.GREEN,
            tail_color=Colors.SOFT_GREEN,
            dot_count=2,
            tail_length=2,
            period=1.5,
        ),
        "state_pulse_wave": PulseWaveEffect(
            color=Colors.SOFT_CYAN,
            period=2.0,
            width=3.0,
        ),
        "state_custom_doa": CustomDoaEffect(
            center_color=Colors.CYAN,
            wing_color=Colors.SOFT_BLUE,
            base_color=RGB(3, 3, 10),
        ),

        # ---- Advanced events ------------------------------------
        "event_timer_10s": TimerCountdownEffect(
            total_seconds=10.0,
            color=Colors.CYAN,
            brightness_steps=8,
        ),
        "event_timer_30s": TimerCountdownEffect(
            total_seconds=30.0,
            color=Colors.GREEN,
            brightness_steps=8,
        ),
        "event_timer_60s": TimerCountdownEffect(
            total_seconds=60.0,
            color=Colors.BLUE,
            brightness_steps=8,
        ),
    }


def build_standard_registry() -> EffectRegistry:
    """Return the standard library wrapped in an ``EffectRegistry``."""
    return EffectRegistry(build_standard_effects())
