from __future__ import annotations

from typing import Any, Callable

from .models import LED_COUNT, Visual


FrameProvider = Callable[[float], list[int | None]]

SUPPORTED_VISUAL_TYPES = {
    "solid",
    "pulse",
    "blink",
    "progress",
    "segments",
    "ring_frame",
    "dynamic_frame",
}


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


def segments(segments_data: list[dict[str, Any]], *, exclusive: bool = False) -> Visual:
    return Visual("segments", {"segments": segments_data}, exclusive=exclusive)


def ring_frame(colors: list[int | None], *, exclusive: bool = False) -> Visual:
    if len(colors) != LED_COUNT:
        raise ValueError(f"ring_frame expects {LED_COUNT} colors")
    return Visual("ring_frame", {"colors": colors}, exclusive=exclusive)


def dynamic_frame(provider: FrameProvider, *, exclusive: bool = False) -> Visual:
    return Visual("dynamic_frame", {"provider": provider}, exclusive=exclusive)


def visual_from_spec(spec: dict[str, Any] | None) -> Visual | None:
    if spec is None:
        return None

    visual_type = str(spec.get("type", "")).strip()
    if visual_type not in SUPPORTED_VISUAL_TYPES:
        raise ValueError(f"Unsupported visual type: {visual_type}")

    params = dict(spec.get("params", {}))
    exclusive = bool(spec.get("exclusive", False))

    if visual_type == "ring_frame":
        colors = list(params.get("colors", []))
        if len(colors) != LED_COUNT:
            raise ValueError(f"ring_frame expects {LED_COUNT} colors")

    if visual_type == "dynamic_frame":
        provider = params.get("provider")
        if not callable(provider):
            raise ValueError("dynamic_frame requires a callable provider")

    return Visual(visual_type, params, exclusive=exclusive)
