from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from led_effects.quick_actions_layer.visuals import dynamic_frame, solid
from respeaker_led_controller.color_math import blend, segment_lengths
from respeaker_led_controller.models import LED_COUNT, WidgetBuildResult
from respeaker_led_controller.spec_utils import parse_hex_color


STATE_COLORS = {
    "pending": 0xFFD166,
    "waiting": 0x8D99AE,
    "approved": 0x00C853,
    "rejected": 0xD90429,
    "expired": 0xFB5607,
}


@dataclass(slots=True)
class ApprovalItem:
    name: str
    state: str
    priority: int = 100
    age_minutes: int = 0
    waiting_on_user: bool = False
    urgent: bool = False


def _render(items: list[ApprovalItem], base_color: int, waiting_color: int, urgent_color: int, pulse_period: float):
    def provider(now: float) -> list[int | None]:
        frame: list[int | None] = [base_color] * LED_COUNT
        cursor = 0
        for item, length in zip(items, segment_lengths(len(items))):
            state = item.state.lower()
            state_color = STATE_COLORS.get(state, 0xFFFFFF)
            start = cursor
            end = cursor + length - 1
            cursor += length

            urgency_mix = min(1.0, max(0, int(item.age_minutes)) / 240.0)
            segment_base = blend(base_color, state_color, 0.12 + urgency_mix * 0.18)
            for index in range(start, end + 1):
                frame[index] = segment_base

            anchor = state_color
            if item.waiting_on_user:
                phase = (math.sin((now / pulse_period) * 2.0 * math.pi) + 1.0) / 2.0
                anchor = blend(state_color, waiting_color, phase * 0.7)
            elif item.urgent:
                phase = (now % 0.8) / 0.8
                anchor = urgent_color if phase < 0.5 else state_color
            frame[start] = anchor

            if length > 1:
                tail_index = end
                if item.urgent:
                    phase = (now % 0.7) / 0.7
                    frame[tail_index] = urgent_color if phase < 0.45 else state_color
                elif item.waiting_on_user:
                    phase = (math.sin((now / pulse_period) * 2.0 * math.pi) + 1.0) / 2.0
                    frame[tail_index] = blend(segment_base, waiting_color, phase)
                else:
                    priority_mix = min(1.0, max(0, int(item.priority)) / 300.0)
                    frame[tail_index] = blend(segment_base, state_color, priority_mix)
        return frame

    return provider


def build_widget(spec: dict) -> WidgetBuildResult:
    raw_items = spec.get("items", [])
    items = [ApprovalItem(**item) for item in raw_items]
    if not items:
        raise ValueError("approval_inbox requires at least one item")
    if len(items) > LED_COUNT:
        raise ValueError(f"approval_inbox supports at most {LED_COUNT} items")

    base_color = parse_hex_color(spec.get("base_color"), 0x020304)
    waiting_color = parse_hex_color(spec.get("waiting_color"), 0xFFFFFF)
    urgent_color = parse_hex_color(spec.get("urgent_color"), 0xFFE08A)
    pulse_period = float(spec.get("pulse_period", 1.4))

    return WidgetBuildResult(
        widget_id="approval_inbox",
        mode="approval_inbox",
        payload={"items": [asdict(item) for item in items]},
        visual=dynamic_frame(_render(items, base_color, waiting_color, urgent_color, pulse_period), exclusive=False),
        background_visual=solid(base_color),
        background_mode="solid",
    )
