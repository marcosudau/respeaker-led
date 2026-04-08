from __future__ import annotations

from .models import LED_COUNT


def clamp_channel(value: float) -> int:
    return max(0, min(255, int(value)))


def rgb(r: float, g: float, b: float) -> int:
    return (clamp_channel(r) << 16) | (clamp_channel(g) << 8) | clamp_channel(b)


def scale_color(color: int, factor: float) -> int:
    factor = max(0.0, factor)
    return rgb(
        ((color >> 16) & 0xFF) * factor,
        ((color >> 8) & 0xFF) * factor,
        (color & 0xFF) * factor,
    )


def blend(color_a: int, color_b: int, mix: float) -> int:
    mix = max(0.0, min(1.0, mix))
    inverse = 1.0 - mix
    return rgb(
        ((color_a >> 16) & 0xFF) * inverse + ((color_b >> 16) & 0xFF) * mix,
        ((color_a >> 8) & 0xFF) * inverse + ((color_b >> 8) & 0xFF) * mix,
        (color_a & 0xFF) * inverse + (color_b & 0xFF) * mix,
    )


def segment_lengths(count: int) -> list[int]:
    if count <= 0:
        return []
    base = LED_COUNT // count
    remainder = LED_COUNT % count
    return [base + (1 if index < remainder else 0) for index in range(count)]


def evenly_spaced_positions(count: int) -> list[int]:
    if count <= 0:
        return []
    step = LED_COUNT / float(count)
    return [int(round(index * step)) % LED_COUNT for index in range(count)]
