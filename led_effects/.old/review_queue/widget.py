from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from led_effects.quick_actions_layer.visuals import dynamic_frame, solid
from respeaker_led_controller.color_math import blend, scale_color, segment_lengths
from respeaker_led_controller.models import LED_COUNT, WidgetBuildResult
from respeaker_led_controller.spec_utils import parse_hex_color


STATE_COLORS = {
    "queued": 0x5C677D,
    "reviewing": 0x00AEEF,
    "changes": 0xFB5607,
    "approved": 0x00C853,
    "merged": 0x9EF01A,
    "blocked": 0xD90429,
}


@dataclass(slots=True)
class ReviewItem:
    name: str
    state: str
    priority: int = 100
    age_minutes: int = 0
    comments: int = 0
    changes_requested: bool = False
    merge_ready: bool = False


def _render(items: list[ReviewItem], base_color: int, ready_color: int, attention_color: int, pulse_period: float):
    def provider(now: float) -> list[int | None]:
        frame: list[int | None] = [base_color] * LED_COUNT
        cursor = 0
        for item, length in zip(items, segment_lengths(len(items))):
            state_color = STATE_COLORS.get(item.state.lower(), 0xFFFFFF)
            start = cursor
            end = cursor + length - 1
            cursor += length

            segment_base = blend(base_color, state_color, 0.12 + min(1.0, max(0, int(item.age_minutes)) / 240.0) * 0.16)
            for index in range(start, end + 1):
                frame[index] = segment_base

            anchor = state_color
            if item.merge_ready:
                phase = (math.sin((now / pulse_period) * 2.0 * math.pi) + 1.0) / 2.0
                anchor = blend(scale_color(state_color, 0.4), ready_color, phase * 0.65)
            elif item.changes_requested or item.state.lower() in {"changes", "blocked"}:
                phase = (now % 0.85) / 0.85
                anchor = state_color if phase < 0.5 else scale_color(state_color, 0.25)
            frame[start] = anchor

            if length > 1:
                tail_index = end
                if item.changes_requested:
                    phase = (now % 0.8) / 0.8
                    frame[tail_index] = attention_color if phase < 0.45 else state_color
                elif item.merge_ready:
                    phase = (math.sin((now / pulse_period) * 2.0 * math.pi) + 1.0) / 2.0
                    frame[tail_index] = blend(segment_base, ready_color, phase)
                else:
                    mix = min(1.0, max(max(0, int(item.priority)) / 300.0, max(0, int(item.comments)) / 6.0))
                    frame[tail_index] = blend(segment_base, state_color, mix)
        return frame

    return provider


def build_widget(spec: dict) -> WidgetBuildResult:
    raw_items = spec.get("items", [])
    items = [ReviewItem(**item) for item in raw_items]
    if not items:
        raise ValueError("review_queue requires at least one item")
    if len(items) > LED_COUNT:
        raise ValueError(f"review_queue supports at most {LED_COUNT} items")

    base_color = parse_hex_color(spec.get("base_color"), 0x020304)
    ready_color = parse_hex_color(spec.get("ready_color"), 0xFFFFFF)
    attention_color = parse_hex_color(spec.get("attention_color"), 0xFFE08A)
    pulse_period = float(spec.get("pulse_period", 1.3))

    return WidgetBuildResult(
        widget_id="review_queue",
        mode="review_queue",
        payload={"items": [asdict(item) for item in items]},
        visual=dynamic_frame(_render(items, base_color, ready_color, attention_color, pulse_period), exclusive=False),
        background_visual=solid(base_color),
        background_mode="solid",
    )
