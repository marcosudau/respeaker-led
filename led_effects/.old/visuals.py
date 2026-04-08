from __future__ import annotations

"""Quick visual primitives shared by the whole controller.

Diese Datei ist bewusst zentral gehalten, weil sie keine Widget-Logik enthaelt,
sondern nur die kleinsten wiederverwendbaren LED-Bausteine:
- Vollflaechen
- Pulse/Blinken
- Progress-Ringe
- statische Ringframes
- dynamische Frame-Provider

Alles, was fachliche Bedeutung hat, gehoert dagegen in ein Widget unter
`led_effects/led_widgets_layer/<widget_name>/`.
"""

from typing import Callable

from respeaker_led_controller.models import LED_COUNT, Visual


FrameProvider = Callable[[float], list[int | None]]


def solid(color: int, *, exclusive: bool = False) -> Visual:
    return Visual("solid", {"color": color}, exclusive=exclusive)


def pulse(
    color: int,
    *,
    base_color: int = 0x000000,
    period: float = 2.0,
    exclusive: bool = False,
) -> Visual:
    return Visual(
        "pulse",
        {"color": color, "base_color": base_color, "period": period},
        exclusive=exclusive,
    )


def blink(
    color: int,
    *,
    base_color: int = 0x000000,
    period: float = 1.0,
    duty_cycle: float = 0.5,
    exclusive: bool = True,
) -> Visual:
    return Visual(
        "blink",
        {
            "color": color,
            "base_color": base_color,
            "period": period,
            "duty_cycle": duty_cycle,
        },
        exclusive=exclusive,
    )


def progress(
    value: float,
    *,
    color: int,
    base_color: int = 0x050505,
    exclusive: bool = False,
) -> Visual:
    return Visual(
        "progress",
        {"value": value, "color": color, "base_color": base_color},
        exclusive=exclusive,
    )


def segments(segments_data: list[dict], *, exclusive: bool = False) -> Visual:
    return Visual("segments", {"segments": segments_data}, exclusive=exclusive)


def ring_frame(colors: list[int | None], *, exclusive: bool = False) -> Visual:
    if len(colors) != LED_COUNT:
        raise ValueError(f"ring_frame expects {LED_COUNT} colors")
    return Visual("ring_frame", {"colors": colors}, exclusive=exclusive)


def dynamic_frame(provider: FrameProvider, *, exclusive: bool = False) -> Visual:
    return Visual("dynamic_frame", {"provider": provider}, exclusive=exclusive)
