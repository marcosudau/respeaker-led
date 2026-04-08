from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from led_effects.quick_actions_layer.visuals import ring_frame, solid
from respeaker_led_controller.models import LED_COUNT, WidgetBuildResult
from respeaker_led_controller.spec_utils import parse_hex_color


@dataclass(slots=True)
class ClockSpec:
    iso: str
    show_seconds: bool = False
    base_color: str | int = "0x010101"
    hour_color: str | int = "0x3A86FF"
    minute_color: str | int = "0xFFD166"
    second_color: str | int = "0xFF4D4D"


def build_widget(spec: dict) -> WidgetBuildResult:
    clock_spec = ClockSpec(**spec)
    when = datetime.fromisoformat(clock_spec.iso)
    base_color = parse_hex_color(clock_spec.base_color, 0x010101)
    hour_color = parse_hex_color(clock_spec.hour_color, 0x3A86FF)
    minute_color = parse_hex_color(clock_spec.minute_color, 0xFFD166)
    second_color = parse_hex_color(clock_spec.second_color, 0xFF4D4D)

    colors = [base_color] * LED_COUNT
    hour_index = int(((when.hour % 12) + (when.minute / 60.0)) % LED_COUNT)
    minute_index = int((when.minute / 60.0) * LED_COUNT) % LED_COUNT
    colors[hour_index] = hour_color
    colors[minute_index] = minute_color
    if clock_spec.show_seconds:
        second_index = int((when.second / 60.0) * LED_COUNT) % LED_COUNT
        colors[second_index] = second_color

    return WidgetBuildResult(
        widget_id="clock",
        mode="clock",
        payload={"clock": asdict(clock_spec)},
        visual=ring_frame(colors, exclusive=False),
        background_visual=solid(base_color),
        background_mode="solid",
    )
