"""Advanced LED effects requiring per-LED ring control.

These effects go beyond simple whole-ring commands and use
``backend.set_ring_colors()`` for individual LED control.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Callable

from .backend import LED_COUNT
from .context import EffectContext
from .effects import LedEffect
from .rgb import RGB, Colors


# ============================================================
# Helper: map degree → center LED index
# ============================================================

def _deg_to_led_index(deg: float) -> int:
    """Map an angle in degrees (0–360) to the closest LED index (0–11)."""
    normalized = deg % 360.0
    return int(round(normalized / 360.0 * LED_COUNT)) % LED_COUNT


# ============================================================
# 1. Custom Direction-of-Arrival (DoA) Effect
# ============================================================

@dataclass
class CustomDoaEffect(LedEffect):
    """Software-rendered direction-of-arrival indicator.

    Features over the hardware DoA:
    - 3-LED wide pointer (center + two neighbours)
    - Separate colours for center and wing LEDs
    - Custom base colour for the remaining LEDs
    - Works as persistent overlay – loops until stopped
    - ``direction_provider`` callback for live DoA updates

    Parameters
    ----------
    direction_deg : float
        Static direction in degrees (0 = north, clockwise).
        Ignored when *direction_provider* is set.
    center_color : RGB
        Colour of the centre LED in the direction pointer.
    wing_color : RGB
        Colour of the two neighbouring LEDs flanking the centre.
    base_color : RGB
        Colour of all other LEDs (background).
    direction_provider : callable, optional
        ``() -> float``  – called every tick to get the current
        direction in degrees. Enables live tracking.
    refresh_interval : float
        Seconds between ring updates (default 0.05 = 20 fps).
    """

    direction_deg: float = 0.0
    center_color: RGB = field(default_factory=lambda: Colors.CYAN)
    wing_color: RGB = field(default_factory=lambda: Colors.SOFT_BLUE)
    base_color: RGB = field(default_factory=lambda: Colors.BLACK)
    direction_provider: Callable[[], float] | None = None
    refresh_interval: float = 0.05

    def run(self, ctx: EffectContext) -> None:
        while not ctx.is_stopped:
            deg = (
                self.direction_provider()
                if self.direction_provider is not None
                else self.direction_deg
            )
            ring = self._build_ring(deg)
            ctx.backend.set_ring_colors(ring)
            if not ctx.sleep(self.refresh_interval):
                return

    def _build_ring(self, deg: float) -> list[RGB]:
        center = _deg_to_led_index(deg)
        ring = [self.base_color] * LED_COUNT
        ring[center] = self.center_color
        ring[(center - 1) % LED_COUNT] = self.wing_color
        ring[(center + 1) % LED_COUNT] = self.wing_color
        return ring


# ============================================================
# 2. Timer Countdown Ring
# ============================================================

@dataclass
class TimerCountdownEffect(LedEffect):
    """Countdown timer visualised on the LED ring.

    The ring starts fully lit and LEDs dim down one by one as time
    passes – like a clock face (12 LEDs = 12 segments).

    Each LED dims in steps within its time slice to show sub-LED
    progress. The last LEDs change colour to indicate urgency.

    Parameters
    ----------
    total_seconds : float
        Total countdown duration.
    color : RGB
        Base colour for most of the ring.
    warn_color : RGB
        Colour for the last 2 LEDs (warning zone).
    critical_color : RGB
        Colour for the very last LED.
    background : RGB
        Colour for fully expired LEDs.
    brightness_steps : int
        Dimming steps per LED (more = smoother, 8 is good).
    tick_flash : bool
        Brief flash at every LED boundary to show the beat.
    on_complete : str | None
        Name of an event effect to play when the timer ends
        (resolved by the caller; this effect itself just ends).
    """

    total_seconds: float = 60.0
    color: RGB = field(default_factory=lambda: Colors.CYAN)
    warn_color: RGB = field(default_factory=lambda: Colors.YELLOW)
    critical_color: RGB = field(default_factory=lambda: Colors.RED)
    background: RGB = field(default_factory=lambda: RGB(5, 5, 5))
    brightness_steps: int = 8
    tick_flash: bool = True
    on_complete: str | None = None

    def run(self, ctx: EffectContext) -> None:
        total = max(0.1, self.total_seconds)
        steps = max(1, self.brightness_steps)
        total_ticks = LED_COUNT * steps
        tick_duration = total / total_ticks
        start = time.monotonic()

        for tick in range(total_ticks):
            if ctx.is_stopped:
                return

            elapsed = time.monotonic() - start
            expected = tick * tick_duration
            delay = max(0.0, expected - elapsed)
            if delay > 0 and not ctx.sleep(delay):
                return

            remaining_ticks = total_ticks - tick - 1
            ring = self._build_ring(remaining_ticks, steps)

            # tick flash: briefly flash the LED that just lost a step
            if self.tick_flash and tick > 0 and tick % steps == 0:
                flash_led = LED_COUNT - (tick // steps)
                if 0 <= flash_led < LED_COUNT:
                    flash_ring = list(ring)
                    flash_ring[flash_led] = Colors.WHITE
                    ctx.backend.set_ring_colors(flash_ring)
                    if not ctx.sleep(min(0.04, tick_duration * 0.3)):
                        return

            ctx.backend.set_ring_colors(ring)

        # Final: all off
        ctx.backend.set_ring_colors([self.background] * LED_COUNT)

    def _build_ring(self, remaining_ticks: int, steps: int) -> list[RGB]:
        ring: list[RGB] = []
        for led_idx in range(LED_COUNT):
            led_ticks = remaining_ticks - led_idx * steps
            if led_ticks >= steps:
                # fully lit
                ring.append(self._led_color(led_idx))
            elif led_ticks <= 0:
                # fully off
                ring.append(self.background)
            else:
                # partially lit – dim proportionally
                factor = led_ticks / steps
                ring.append(self._led_color(led_idx).scaled(factor))
        return ring

    def _led_color(self, led_idx: int) -> RGB:
        """Determine colour based on LED position (urgency zones)."""
        remaining_from_end = LED_COUNT - 1 - led_idx
        if remaining_from_end == 0:
            return self.critical_color
        if remaining_from_end <= 1:
            return self.warn_color
        return self.color


# ============================================================
# 3. Smooth Progress Ring
# ============================================================

@dataclass
class ProgressRingEffect(LedEffect):
    """Smooth progress ring with sub-LED brightness resolution.

    With 12 LEDs and 8 brightness steps per LED the ring provides
    ~96 distinct levels (≈ 1 % per step).

    Parameters
    ----------
    progress_provider : callable
        ``() -> float``  – returns current progress 0.0 … 1.0.
    color : RGB
        Colour for the filled portion.
    tip_color : RGB | None
        Optional highlight colour for the leading edge LED.
    background : RGB
        Colour for the unfilled portion.
    brightness_steps : int
        Sub-LED brightness levels (default 8).
    refresh_interval : float
        Seconds between updates (default 0.04 = 25 fps).
    clockwise : bool
        Fill direction (True = index 0 → 11).
    """

    progress_provider: Callable[[], float] = field(default_factory=lambda: lambda: 0.0)
    color: RGB = field(default_factory=lambda: Colors.CYAN)
    tip_color: RGB | None = None
    background: RGB = field(default_factory=lambda: RGB(3, 3, 3))
    brightness_steps: int = 8
    refresh_interval: float = 0.04
    clockwise: bool = True

    def run(self, ctx: EffectContext) -> None:
        while not ctx.is_stopped:
            progress = max(0.0, min(1.0, self.progress_provider()))
            ring = self._build_ring(progress)
            ctx.backend.set_ring_colors(ring)
            if not ctx.sleep(self.refresh_interval):
                return

    def _build_ring(self, progress: float) -> list[RGB]:
        steps = max(1, self.brightness_steps)
        total_steps = LED_COUNT * steps
        filled_steps = progress * total_steps

        ring: list[RGB] = []
        for led_idx in range(LED_COUNT):
            actual_idx = led_idx if self.clockwise else (LED_COUNT - 1 - led_idx)
            led_start = actual_idx * steps
            led_fill = max(0.0, min(float(steps), filled_steps - led_start))

            if led_fill >= steps:
                ring.append(self.color)
            elif led_fill <= 0:
                ring.append(self.background)
            else:
                factor = led_fill / steps
                blended = self.background.blend(self.color, factor)
                ring.append(blended)

        # highlight the leading edge
        if self.tip_color is not None and 0.0 < progress < 1.0:
            tip_pos = int(filled_steps / steps)
            if self.clockwise:
                if 0 <= tip_pos < LED_COUNT:
                    ring[tip_pos] = self.tip_color
            else:
                mapped = LED_COUNT - 1 - tip_pos
                if 0 <= mapped < LED_COUNT:
                    ring[mapped] = self.tip_color

        return ring


# ============================================================
# 4. Rotating Spinner Effect
# ============================================================

@dataclass
class SpinnerEffect(LedEffect):
    """One or more dots rotating around the ring.

    Great for indeterminate loading / processing states.

    Parameters
    ----------
    color : RGB
        Colour of the spinning dot(s).
    tail_color : RGB | None
        If set, trailing LEDs get this colour (comet tail).
    background : RGB
        Ring background colour.
    dot_count : int
        Number of evenly spaced dots (1–12).
    tail_length : int
        How many LEDs trail behind each dot (0 = no tail).
    period : float
        Seconds for one full revolution.
    clockwise : bool
        Rotation direction.
    """

    color: RGB = field(default_factory=lambda: Colors.BLUE)
    tail_color: RGB | None = None
    background: RGB = field(default_factory=lambda: Colors.BLACK)
    dot_count: int = 1
    tail_length: int = 2
    period: float = 1.2
    clockwise: bool = True

    def run(self, ctx: EffectContext) -> None:
        start = time.monotonic()
        dots = max(1, min(LED_COUNT, self.dot_count))
        spacing = LED_COUNT / dots

        while not ctx.is_stopped:
            elapsed = time.monotonic() - start
            phase = (elapsed / max(0.05, self.period)) % 1.0
            if not self.clockwise:
                phase = 1.0 - phase

            head_pos = phase * LED_COUNT

            ring = [self.background] * LED_COUNT

            for d in range(dots):
                dot_head = (head_pos + d * spacing) % LED_COUNT
                head_idx = int(round(dot_head)) % LED_COUNT
                ring[head_idx] = self.color

                # tail
                tail_col = self.tail_color if self.tail_color is not None else self.color
                for t in range(1, self.tail_length + 1):
                    tail_idx = (head_idx - t) % LED_COUNT
                    fade = 1.0 - (t / (self.tail_length + 1))
                    ring[tail_idx] = self.background.blend(tail_col, fade)

            ctx.backend.set_ring_colors(ring)
            if not ctx.sleep(0.03):
                return


# ============================================================
# 5. Pulse Wave Effect
# ============================================================

@dataclass
class PulseWaveEffect(LedEffect):
    """A brightness wave that travels around the ring.

    Unlike simple pulsing (entire ring), this creates a spatial
    wave – a bright peak that orbits the ring, giving a lively
    "scanning" or "breathing" look.

    Parameters
    ----------
    color : RGB
        Peak colour of the wave.
    background : RGB
        Base ring colour.
    period : float
        Seconds for the wave to travel one full revolution.
    width : float
        How many LEDs the bright peak spans (gaussian width, 1.0–6.0).
    min_brightness : float
        Minimum brightness factor for non-peak LEDs (0.0–1.0).
    """

    color: RGB = field(default_factory=lambda: Colors.SOFT_CYAN)
    background: RGB = field(default_factory=lambda: Colors.BLACK)
    period: float = 2.0
    width: float = 3.0
    min_brightness: float = 0.05

    def run(self, ctx: EffectContext) -> None:
        start = time.monotonic()
        while not ctx.is_stopped:
            elapsed = time.monotonic() - start
            phase = (elapsed / max(0.1, self.period)) % 1.0
            center = phase * LED_COUNT

            ring: list[RGB] = []
            for i in range(LED_COUNT):
                # circular distance
                raw_dist = abs(i - center)
                dist = min(raw_dist, LED_COUNT - raw_dist)
                sigma = max(0.5, self.width) / 2.0
                brightness = math.exp(-(dist ** 2) / (2.0 * sigma ** 2))
                brightness = max(self.min_brightness, brightness)
                ring.append(self.background.blend(self.color, brightness))

            ctx.backend.set_ring_colors(ring)
            if not ctx.sleep(0.03):
                return


# ============================================================
# 6. Segment Meter Effect
# ============================================================

@dataclass
class SegmentMeterEffect(LedEffect):
    """Multi-colour segment meter (VU-meter / level indicator).

    Divides the ring into coloured zones (green → yellow → red)
    and fills them based on a live level value. Perfect for
    audio level, CPU load, temperature, or any 0–100 % metric.

    Parameters
    ----------
    level_provider : callable
        ``() -> float``  – returns current level 0.0 … 1.0.
    low_color : RGB
        Colour for the lower zone (0–60 %).
    mid_color : RGB
        Colour for the middle zone (60–85 %).
    high_color : RGB
        Colour for the upper zone (85–100 %).
    background : RGB
        Background for unlit LEDs.
    refresh_interval : float
        Update rate in seconds.
    """

    level_provider: Callable[[], float] = field(default_factory=lambda: lambda: 0.0)
    low_color: RGB = field(default_factory=lambda: Colors.GREEN)
    mid_color: RGB = field(default_factory=lambda: Colors.YELLOW)
    high_color: RGB = field(default_factory=lambda: Colors.RED)
    background: RGB = field(default_factory=lambda: RGB(3, 3, 3))
    refresh_interval: float = 0.05

    def run(self, ctx: EffectContext) -> None:
        while not ctx.is_stopped:
            level = max(0.0, min(1.0, self.level_provider()))
            ring = self._build_ring(level)
            ctx.backend.set_ring_colors(ring)
            if not ctx.sleep(self.refresh_interval):
                return

    def _build_ring(self, level: float) -> list[RGB]:
        active = int(round(level * LED_COUNT))
        ring: list[RGB] = []
        for i in range(LED_COUNT):
            if i >= active:
                ring.append(self.background)
            else:
                frac = i / LED_COUNT
                if frac < 0.6:
                    ring.append(self.low_color)
                elif frac < 0.85:
                    ring.append(self.mid_color)
                else:
                    ring.append(self.high_color)
        return ring
