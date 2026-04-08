"""Parametrised LED effect building blocks."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .context import EffectContext
from .rgb import RGB


class LedEffect(ABC):
    """Base class for all LED effects."""

    @abstractmethod
    def run(self, ctx: EffectContext) -> None:
        raise NotImplementedError


# ============================================================
# Primitive effects
# ============================================================


@dataclass
class OffEffect(LedEffect):
    """Turn LEDs off, optionally hold for a duration."""

    hold_seconds: float = 0.0

    def run(self, ctx: EffectContext) -> None:
        ctx.backend.off()
        if self.hold_seconds > 0:
            ctx.sleep(self.hold_seconds)


@dataclass
class StaticColorEffect(LedEffect):
    """Show a single static colour on the entire ring."""

    color: RGB
    hold_seconds: float = 0.0
    persistent: bool = False

    def run(self, ctx: EffectContext) -> None:
        ctx.backend.single_color(self.color)
        if self.persistent:
            ctx.wait_until_stopped()
        elif self.hold_seconds > 0:
            ctx.sleep(self.hold_seconds)


@dataclass
class BreathEffect(LedEffect):
    """Hardware breathing animation."""

    color: RGB
    speed: int = 1
    brightness: int = 128
    hold_seconds: float = 0.0
    persistent: bool = False

    def run(self, ctx: EffectContext) -> None:
        ctx.backend.breath(
            color=self.color,
            speed=self.speed,
            brightness=self.brightness,
        )
        if self.persistent:
            ctx.wait_until_stopped()
        elif self.hold_seconds > 0:
            ctx.sleep(self.hold_seconds)


@dataclass
class RainbowEffect(LedEffect):
    """Hardware rainbow animation."""

    speed: int = 1
    brightness: int = 128
    hold_seconds: float = 0.0
    persistent: bool = False

    def run(self, ctx: EffectContext) -> None:
        ctx.backend.rainbow(speed=self.speed, brightness=self.brightness)
        if self.persistent:
            ctx.wait_until_stopped()
        elif self.hold_seconds > 0:
            ctx.sleep(self.hold_seconds)


@dataclass
class DoaEffect(LedEffect):
    """Direction-of-arrival overlay effect."""

    base_color: RGB
    doa_color: RGB
    hold_seconds: float = 0.0
    persistent: bool = False

    def run(self, ctx: EffectContext) -> None:
        ctx.backend.doa(self.base_color, self.doa_color)
        if self.persistent:
            ctx.wait_until_stopped()
        elif self.hold_seconds > 0:
            ctx.sleep(self.hold_seconds)


@dataclass
class BlinkEffect(LedEffect):
    """Blink a colour on/off with configurable timing.

    ``repeat=None`` means loop until stopped.
    """

    color: RGB
    on_seconds: float = 0.15
    off_seconds: float = 0.15
    repeat: int | None = None

    def run(self, ctx: EffectContext) -> None:
        count = 0
        while not ctx.is_stopped:
            ctx.backend.single_color(self.color)
            if not ctx.sleep(self.on_seconds):
                return

            ctx.backend.off()
            if not ctx.sleep(self.off_seconds):
                return

            count += 1
            if self.repeat is not None and count >= self.repeat:
                return


@dataclass
class AlternateColorEffect(LedEffect):
    """Cycle through a list of colours.

    ``repeat=None`` means loop until stopped.
    """

    colors: list[RGB] = field(default_factory=list)
    interval_seconds: float = 0.3
    repeat: int | None = None

    def run(self, ctx: EffectContext) -> None:
        if not self.colors:
            return

        cycles = 0
        while not ctx.is_stopped:
            for color in self.colors:
                if ctx.is_stopped:
                    return
                ctx.backend.single_color(color)
                if not ctx.sleep(self.interval_seconds):
                    return

            cycles += 1
            if self.repeat is not None and cycles >= self.repeat:
                return


@dataclass
class FadeEffect(LedEffect):
    """Software fade between two colours over a duration."""

    from_color: RGB
    to_color: RGB
    duration: float = 1.0
    steps: int = 20

    def run(self, ctx: EffectContext) -> None:
        actual_steps = max(1, self.steps)
        step_time = max(0.0, self.duration) / actual_steps
        for i in range(actual_steps + 1):
            if ctx.is_stopped:
                return
            ratio = i / actual_steps
            color = self.from_color.blend(self.to_color, ratio)
            ctx.backend.single_color(color)
            if i < actual_steps and not ctx.sleep(step_time):
                return


@dataclass
class SequenceEffect(LedEffect):
    """Run a list of effects in order, optionally repeating."""

    effects: list[LedEffect] = field(default_factory=list)
    repeat: int = 1

    def run(self, ctx: EffectContext) -> None:
        for _ in range(max(1, self.repeat)):
            for effect in self.effects:
                if ctx.is_stopped:
                    return
                effect.run(ctx)
                if ctx.is_stopped:
                    return
