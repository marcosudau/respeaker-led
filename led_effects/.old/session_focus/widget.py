from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from led_effects.quick_actions_layer.visuals import dynamic_frame, solid
from respeaker_led_controller.color_math import blend, scale_color, segment_lengths
from respeaker_led_controller.models import LED_COUNT, WidgetBuildResult
from respeaker_led_controller.spec_utils import parse_hex_color


STATE_COLORS = {
    "focused": 0x00AEEF,
    "active": 0x00C853,
    "waiting": 0xFFD166,
    "idle": 0x5C677D,
    "paused": 0x8D99AE,
    "blocked": 0xFF3D00,
    "done": 0x9EF01A,
}


@dataclass(slots=True)
class SessionStatus:
    name: str
    state: str
    focus_score: float = 0.0
    active_tasks: int = 0
    unread_events: int = 0
    is_focused: bool = False
    pinned: bool = False
    stale: bool = False


def _render(sessions: list[SessionStatus], base_color: int, focus_color: int, attention_color: int, pulse_period: float):
    def provider(now: float) -> list[int | None]:
        frame: list[int | None] = [base_color] * LED_COUNT
        cursor = 0
        for session, length in zip(sessions, segment_lengths(len(sessions))):
            state = session.state.lower()
            state_color = STATE_COLORS.get(state, 0xFFFFFF)
            start = cursor
            end = cursor + length - 1
            cursor += length

            focus_score = max(0.0, min(100.0, float(session.focus_score)))
            segment_base = blend(base_color, state_color, 0.12 + (focus_score / 100.0) * 0.12)
            for index in range(start, end + 1):
                frame[index] = segment_base

            anchor = state_color
            if session.is_focused:
                phase = (math.sin((now / pulse_period) * 2.0 * math.pi) + 1.0) / 2.0
                anchor = blend(scale_color(state_color, 0.35), focus_color, phase * 0.7)
            elif state == "blocked":
                phase = (now % 0.8) / 0.8
                anchor = state_color if phase < 0.55 else scale_color(state_color, 0.25)
            elif state == "done":
                anchor = blend(segment_base, state_color, 0.95)
            frame[start] = anchor

            reserve_tail = length > 1 and (session.unread_events > 0 or session.stale or session.pinned or session.is_focused)
            middle_slots = max(0, length - 1 - (1 if reserve_tail else 0))
            fill_count = min(middle_slots, max(0, int(session.active_tasks)))
            fill_color = blend(segment_base, state_color, 0.8)
            for offset in range(fill_count):
                frame[start + 1 + offset] = fill_color

            if length > 1:
                tail_index = end
                if session.stale:
                    phase = (now % 0.9) / 0.9
                    frame[tail_index] = attention_color if phase < 0.5 else scale_color(attention_color, 0.2)
                elif session.unread_events > 0:
                    phase = (now % 0.75) / 0.75
                    frame[tail_index] = attention_color if phase < 0.45 else state_color
                elif session.is_focused:
                    phase = (math.sin((now / pulse_period) * 2.0 * math.pi) + 1.0) / 2.0
                    frame[tail_index] = blend(segment_base, focus_color, phase)
                elif session.pinned:
                    frame[tail_index] = blend(segment_base, focus_color, 0.7)
        return frame

    return provider


def build_widget(spec: dict) -> WidgetBuildResult:
    raw_sessions = spec.get("sessions", [])
    sessions = [SessionStatus(**item) for item in raw_sessions]
    if not sessions:
        raise ValueError("session_focus requires at least one session")
    if len(sessions) > LED_COUNT:
        raise ValueError(f"session_focus supports at most {LED_COUNT} sessions")

    base_color = parse_hex_color(spec.get("base_color"), 0x020304)
    focus_color = parse_hex_color(spec.get("focus_color"), 0xFFFFFF)
    attention_color = parse_hex_color(spec.get("attention_color"), 0xFFE08A)
    pulse_period = float(spec.get("pulse_period", 1.6))

    return WidgetBuildResult(
        widget_id="session_focus",
        mode="session_focus",
        payload={"sessions": [asdict(session) for session in sessions]},
        visual=dynamic_frame(_render(sessions, base_color, focus_color, attention_color, pulse_period), exclusive=False),
        background_visual=solid(base_color),
        background_mode="solid",
    )
