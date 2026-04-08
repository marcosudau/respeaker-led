from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from led_effects.quick_actions_layer.visuals import dynamic_frame, solid
from respeaker_led_controller.color_math import blend, scale_color, segment_lengths
from respeaker_led_controller.models import LED_COUNT, WidgetBuildResult
from respeaker_led_controller.spec_utils import parse_hex_color


STATE_COLORS = {
    "idle": 0x303030,
    "queued": 0x5C677D,
    "busy": 0x00AEEF,
    "running": 0x00AEEF,
    "done": 0x00C853,
    "approval": 0xFF8800,
    "review": 0xFF8800,
    "blocked": 0xFF3D00,
    "error": 0xFF1744,
    "paused": 0x8D99AE,
}


@dataclass(slots=True)
class ProjectStatus:
    name: str
    state: str
    active_agents: int = 0
    max_agents: int = 1
    progress: float | None = None
    approval_required: bool = False
    needs_attention: bool = False


def _anchor_color(state: str, state_color: int, now: float, pulse_period: float) -> int:
    if state in {"busy", "running"}:
        phase = (math.sin((now / pulse_period) * 2.0 * math.pi) + 1.0) / 2.0
        return blend(scale_color(state_color, 0.45), state_color, phase)
    if state in {"approval", "review"}:
        phase = (math.sin((now / 1.2) * 2.0 * math.pi) + 1.0) / 2.0
        return blend(scale_color(state_color, 0.6), 0xFFFFFF, phase * 0.35)
    if state in {"blocked", "error"}:
        phase = (now % 0.8) / 0.8
        return state_color if phase < 0.5 else scale_color(state_color, 0.2)
    if state == "done":
        return blend(scale_color(state_color, 0.6), state_color, 0.85)
    if state == "queued":
        return blend(scale_color(state_color, 0.45), state_color, 0.5)
    if state == "paused":
        return scale_color(state_color, 0.6)
    return state_color


def _render(projects: list[ProjectStatus], base_color: int, approval_color: int, attention_color: int, pulse_period: float):
    def provider(now: float) -> list[int | None]:
        frame: list[int | None] = [base_color] * LED_COUNT
        cursor = 0
        for project, length in zip(projects, segment_lengths(len(projects))):
            state = project.state.lower()
            state_color = STATE_COLORS.get(state, 0xFFFFFF)
            start = cursor
            end = cursor + length - 1
            cursor += length

            segment_base = blend(base_color, state_color, 0.14)
            for index in range(start, end + 1):
                frame[index] = segment_base
            frame[start] = _anchor_color(state, state_color, now, pulse_period)

            reserve_tail = length > 1 and (
                project.approval_required
                or project.needs_attention
                or project.progress is not None
                or state in {"approval", "review", "blocked", "error", "done"}
            )
            agent_slots = max(0, length - 1 - (1 if reserve_tail else 0))
            max_agents = max(1, int(project.max_agents))
            active_agents = max(0, int(project.active_agents))
            occupancy = min(agent_slots, int(round((min(active_agents, max_agents) / max_agents) * agent_slots)))
            agent_color = blend(segment_base, state_color, 0.8)
            for offset in range(occupancy):
                frame[start + 1 + offset] = agent_color

            if length > 1:
                tail_index = end
                if project.approval_required or state in {"approval", "review"}:
                    phase = (now % 0.9) / 0.9
                    frame[tail_index] = approval_color if phase < 0.55 else state_color
                elif project.needs_attention or state in {"blocked", "error"}:
                    phase = (now % 0.7) / 0.7
                    frame[tail_index] = attention_color if phase < 0.5 else state_color
                elif project.progress is not None:
                    progress_mix = max(0.0, min(1.0, float(project.progress) / 100.0))
                    frame[tail_index] = blend(segment_base, state_color, progress_mix)
                elif state == "done":
                    frame[tail_index] = blend(segment_base, state_color, 0.95)
        return frame

    return provider


def build_widget(spec: dict) -> WidgetBuildResult:
    raw_projects = spec.get("projects", [])
    projects = [ProjectStatus(**item) for item in raw_projects]
    if not projects:
        raise ValueError("project_agents requires at least one project")
    if len(projects) > LED_COUNT:
        raise ValueError(f"project_agents supports at most {LED_COUNT} projects")

    base_color = parse_hex_color(spec.get("base_color"), 0x020304)
    approval_color = parse_hex_color(spec.get("approval_color"), 0xFFFFFF)
    attention_color = parse_hex_color(spec.get("attention_color"), 0xFFE08A)
    pulse_period = float(spec.get("pulse_period", 1.8))

    return WidgetBuildResult(
        widget_id="project_agents",
        mode="project_agents",
        payload={"projects": [asdict(project) for project in projects]},
        visual=dynamic_frame(_render(projects, base_color, approval_color, attention_color, pulse_period), exclusive=False),
        background_visual=solid(base_color),
        background_mode="solid",
    )
