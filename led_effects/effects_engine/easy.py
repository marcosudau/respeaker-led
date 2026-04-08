"""Very small beginner-friendly facade over the effects engine.

This module intentionally hides most architecture details behind a tiny API:

    from led_effects.effects_engine import easy_hardware

    ring = easy_hardware()
    ring.color("blue")
    ring.spinner(seconds=5)
    ring.off()

The advanced controller API still exists unchanged for more complex use cases.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .advanced_effects import (
    CustomDoaEffect,
    ProgressRingEffect,
    PulseWaveEffect,
    SegmentMeterEffect,
    SpinnerEffect,
    TimerCountdownEffect,
)
from .backend import DryRunBackend, LedRingBackend, XvfHostBackend
from .config_loader import parse_color
from .context import EffectContext
from .controller import LedRingController
from .effects import BlinkEffect, BreathEffect, DoaEffect, LedEffect, RainbowEffect, StaticColorEffect
from .rgb import Colors, RGB


def _default_xvf_host_path() -> Path:
    return Path(__file__).resolve().parents[2] / "python_control" / "xvf_host.py"


@dataclass
class _RingFrameEffect(LedEffect):
    colors: list[RGB]
    hold_seconds: float = 0.0

    def run(self, ctx: EffectContext) -> None:
        ctx.backend.set_ring_colors(self.colors)
        if self.hold_seconds > 0:
            ctx.sleep(self.hold_seconds)


class EasyLedRing:
    """Small wrapper that makes the common LED actions trivial.

    Designed for the "I just want lights now" workflow.
    """

    def __init__(
        self,
        backend: LedRingBackend,
        *,
        controller: LedRingController | None = None,
    ) -> None:
        self.backend = backend
        self.controller = controller or LedRingController(backend)
        self._temp_counter = itertools.count()

    @classmethod
    def hardware(
        cls,
        host_path: str | Path | None = None,
        **backend_kwargs: Any,
    ) -> EasyLedRing:
        backend = XvfHostBackend(
            host_path or _default_xvf_host_path(),
            **backend_kwargs,
        )
        return cls(backend)

    @classmethod
    def preview(cls, logger=print) -> EasyLedRing:
        return cls(DryRunBackend(logger=logger))

    def wait(self, seconds: float) -> EasyLedRing:
        time.sleep(max(0.0, seconds))
        return self

    def off(self) -> EasyLedRing:
        self.controller.stop_all(turn_off=True)
        return self

    stop = off

    def choices(self) -> dict[str, list[str]]:
        return {
            "states": [name.removeprefix("state_") for name in self.controller.effects.list_by_group("state_")],
            "events": [name.removeprefix("event_") for name in self.controller.effects.list_by_group("event_")],
            "system": [name.removeprefix("system_") for name in self.controller.effects.list_by_group("system_")],
        }

    def list_all(self) -> list[str]:
        return self.controller.list_effects()

    def show(self, name: str, *, seconds: float | None = None) -> EasyLedRing:
        resolved = self._resolve_effect_name(name)
        if resolved.startswith(("event_", "system_")):
            self.controller.play_event(resolved, asynchronous=False)
            return self

        self.controller.set_state(resolved)
        if seconds is not None:
            self.wait(seconds)
            self.off()
        return self

    def color(self, color: RGB | str | tuple[int, int, int] | list[int], *, seconds: float | None = None) -> EasyLedRing:
        effect = StaticColorEffect(color=parse_color(color), persistent=True)
        return self._show_temp_state(effect, seconds=seconds)

    def breathe(
        self,
        color: RGB | str | tuple[int, int, int] | list[int] = "cyan",
        *,
        speed: int = 1,
        brightness: int = 90,
        seconds: float | None = None,
    ) -> EasyLedRing:
        effect = BreathEffect(
            color=parse_color(color),
            speed=speed,
            brightness=brightness,
            persistent=True,
        )
        return self._show_temp_state(effect, seconds=seconds)

    def rainbow(
        self,
        *,
        speed: int = 1,
        brightness: int = 128,
        seconds: float | None = None,
    ) -> EasyLedRing:
        effect = RainbowEffect(speed=speed, brightness=brightness, persistent=True)
        return self._show_temp_state(effect, seconds=seconds)

    def doa(
        self,
        *,
        base_color: RGB | str | tuple[int, int, int] | list[int] = "soft_blue",
        doa_color: RGB | str | tuple[int, int, int] | list[int] = "yellow",
        seconds: float | None = None,
    ) -> EasyLedRing:
        effect = DoaEffect(
            base_color=parse_color(base_color),
            doa_color=parse_color(doa_color),
            persistent=True,
        )
        return self._show_temp_state(effect, seconds=seconds)

    def blink(
        self,
        color: RGB | str | tuple[int, int, int] | list[int] = "yellow",
        *,
        times: int = 2,
        on_seconds: float = 0.15,
        off_seconds: float = 0.15,
    ) -> EasyLedRing:
        effect = BlinkEffect(
            color=parse_color(color),
            on_seconds=on_seconds,
            off_seconds=off_seconds,
            repeat=max(1, times),
        )
        return self._play_temp_event(effect)

    def spinner(
        self,
        *,
        color: RGB | str | tuple[int, int, int] | list[int] = "cyan",
        tail_color: RGB | str | tuple[int, int, int] | list[int] | None = "soft_blue",
        dots: int = 1,
        tail_length: int = 3,
        period: float = 1.0,
        clockwise: bool = True,
        seconds: float | None = None,
    ) -> EasyLedRing:
        effect = SpinnerEffect(
            color=parse_color(color),
            tail_color=parse_color(tail_color) if tail_color is not None else None,
            background=Colors.BLACK,
            dot_count=dots,
            tail_length=tail_length,
            period=period,
            clockwise=clockwise,
        )
        return self._show_temp_state(effect, seconds=seconds)

    def pulse_wave(
        self,
        *,
        color: RGB | str | tuple[int, int, int] | list[int] = "soft_cyan",
        period: float = 2.0,
        width: float = 3.0,
        seconds: float | None = None,
    ) -> EasyLedRing:
        effect = PulseWaveEffect(
            color=parse_color(color),
            period=period,
            width=width,
        )
        return self._show_temp_state(effect, seconds=seconds)

    def timer(self, seconds: float = 10.0) -> EasyLedRing:
        effect = TimerCountdownEffect(total_seconds=max(0.1, seconds))
        return self._play_temp_event(effect)

    def progress(
        self,
        value: float,
        *,
        color: RGB | str | tuple[int, int, int] | list[int] = "green",
        tip_color: RGB | str | tuple[int, int, int] | list[int] | None = "white",
        background: RGB | str | tuple[int, int, int] | list[int] = (3, 3, 3),
        brightness_steps: int = 8,
        hold_seconds: float = 0.0,
    ) -> EasyLedRing:
        effect = ProgressRingEffect(
            color=parse_color(color),
            tip_color=parse_color(tip_color) if tip_color is not None else None,
            background=parse_color(background),
            brightness_steps=brightness_steps,
        )
        ring = effect._build_ring(max(0.0, min(1.0, value)))
        return self._play_temp_event(_RingFrameEffect(ring, hold_seconds=hold_seconds))

    def meter(
        self,
        value: float,
        *,
        low_color: RGB | str | tuple[int, int, int] | list[int] = "green",
        mid_color: RGB | str | tuple[int, int, int] | list[int] = "yellow",
        high_color: RGB | str | tuple[int, int, int] | list[int] = "red",
        background: RGB | str | tuple[int, int, int] | list[int] = (3, 3, 3),
        hold_seconds: float = 0.0,
    ) -> EasyLedRing:
        effect = SegmentMeterEffect(
            low_color=parse_color(low_color),
            mid_color=parse_color(mid_color),
            high_color=parse_color(high_color),
            background=parse_color(background),
        )
        ring = effect._build_ring(max(0.0, min(1.0, value)))
        return self._play_temp_event(_RingFrameEffect(ring, hold_seconds=hold_seconds))

    def pointer(
        self,
        degrees: float,
        *,
        center_color: RGB | str | tuple[int, int, int] | list[int] = "cyan",
        wing_color: RGB | str | tuple[int, int, int] | list[int] = "soft_blue",
        base_color: RGB | str | tuple[int, int, int] | list[int] = "black",
        hold_seconds: float = 0.0,
    ) -> EasyLedRing:
        effect = CustomDoaEffect(
            direction_deg=degrees,
            center_color=parse_color(center_color),
            wing_color=parse_color(wing_color),
            base_color=parse_color(base_color),
        )
        ring = effect._build_ring(degrees)
        return self._play_temp_event(_RingFrameEffect(ring, hold_seconds=hold_seconds))

    def _show_temp_state(self, effect: LedEffect, *, seconds: float | None) -> EasyLedRing:
        name = self._register_temp("state", effect)
        self.controller.set_state(name)
        if seconds is not None:
            self.wait(seconds)
            self.off()
        return self

    def _play_temp_event(self, effect: LedEffect) -> EasyLedRing:
        name = self._register_temp("event", effect)
        self.controller.play_event(name, asynchronous=False)
        return self

    def _register_temp(self, kind: str, effect: LedEffect) -> str:
        name = f"__easy_{kind}_{next(self._temp_counter)}"
        self.controller.register_effect(name, effect)
        return name

    def _resolve_effect_name(self, name: str) -> str:
        normalized = str(name).strip().lower().replace("-", "_")
        if self.controller.effects.has(normalized):
            return normalized

        candidates = [
            f"state_{normalized}",
            f"event_{normalized}",
            f"system_{normalized}",
        ]
        matches = [candidate for candidate in candidates if self.controller.effects.has(candidate)]

        if len(matches) == 1:
            return matches[0]

        if len(matches) > 1:
            raise KeyError(
                f"Ambiguous easy effect name '{name}'. Matches: {', '.join(matches)}"
            )

        available = sorted(
            {
                *self.choices()["states"],
                *self.choices()["events"],
                *self.choices()["system"],
            }
        )
        raise KeyError(
            f"Unknown easy effect '{name}'. Try one of: {', '.join(available)}"
        )


def easy_hardware(
    host_path: str | Path | None = None,
    **backend_kwargs: Any,
) -> EasyLedRing:
    return EasyLedRing.hardware(host_path=host_path, **backend_kwargs)


def easy_preview(logger=print) -> EasyLedRing:
    return EasyLedRing.preview(logger=logger)