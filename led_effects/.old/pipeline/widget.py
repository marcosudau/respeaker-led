from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from led_effects.quick_actions_layer.visuals import dynamic_frame, solid
from respeaker_led_controller.color_math import blend, scale_color, segment_lengths
from respeaker_led_controller.models import LED_COUNT, WidgetBuildResult
from respeaker_led_controller.spec_utils import parse_hex_color


STATE_COLORS = {
    "queued": 0x5C677D,
    "running": 0x00AEEF,
    "passed": 0x00C853,
    "done": 0x00C853,
    "review": 0xFFB703,
    "waiting": 0x8D99AE,
    "blocked": 0xFB5607,
    "failed": 0xD90429,
    "skipped": 0x495057,
}


@dataclass(slots=True)
class PipelineStage:
    name: str
    state: str
    progress: float | None = None
    active_jobs: int = 0
    max_jobs: int = 1
    is_current: bool = False
    blocked: bool = False
    needs_attention: bool = False


def _render(stages: list[PipelineStage], base_color: int, current_color: int, attention_color: int, pulse_period: float):
    def provider(now: float) -> list[int | None]:
        frame: list[int | None] = [base_color] * LED_COUNT
        cursor = 0
        for stage, length in zip(stages, segment_lengths(len(stages))):
            state = stage.state.lower()
            state_color = STATE_COLORS.get(state, 0xFFFFFF)
            start = cursor
            end = cursor + length - 1
            cursor += length

            segment_base = blend(base_color, state_color, 0.12)
            for index in range(start, end + 1):
                frame[index] = segment_base

            anchor = state_color
            if stage.is_current:
                phase = (math.sin((now / pulse_period) * 2.0 * math.pi) + 1.0) / 2.0
                anchor = blend(scale_color(state_color, 0.4), current_color, phase * 0.65)
            elif state in {"failed", "blocked"}:
                phase = (now % 0.9) / 0.9
                anchor = state_color if phase < 0.55 else scale_color(state_color, 0.25)
            elif state in {"passed", "done"}:
                anchor = blend(segment_base, state_color, 0.95)
            frame[start] = anchor

            reserve_tail = length > 1 and (
                stage.blocked
                or stage.needs_attention
                or stage.progress is not None
                or stage.is_current
                or state in {"failed", "blocked", "review", "running"}
            )
            middle_slots = max(0, length - 1 - (1 if reserve_tail else 0))
            max_jobs = max(1, int(stage.max_jobs))
            active_jobs = max(0, int(stage.active_jobs))
            progress_value = stage.progress
            ratio = ((max(0.0, min(100.0, float(progress_value))) / 100.0) if progress_value is not None else (min(active_jobs, max_jobs) / max_jobs))
            fill_count = min(middle_slots, int(round(ratio * middle_slots)))
            fill_color = blend(segment_base, state_color, 0.82)
            for offset in range(fill_count):
                frame[start + 1 + offset] = fill_color

            if length > 1:
                tail_index = end
                if stage.blocked or state == "blocked":
                    phase = (now % 0.7) / 0.7
                    frame[tail_index] = attention_color if phase < 0.45 else state_color
                elif stage.needs_attention or state in {"failed", "review"}:
                    phase = (now % 0.85) / 0.85
                    frame[tail_index] = attention_color if phase < 0.5 else state_color
                elif stage.is_current:
                    phase = (math.sin((now / pulse_period) * 2.0 * math.pi) + 1.0) / 2.0
                    frame[tail_index] = blend(segment_base, current_color, phase)
                elif progress_value is not None:
                    progress_mix = max(0.0, min(1.0, float(progress_value) / 100.0))
                    frame[tail_index] = blend(segment_base, state_color, progress_mix)
                elif state in {"passed", "done"}:
                    frame[tail_index] = blend(segment_base, state_color, 0.95)
        return frame

    return provider


def build_widget(spec: dict) -> WidgetBuildResult:
    raw_stages = spec.get("stages", [])
    stages = [PipelineStage(**item) for item in raw_stages]
    if not stages:
        raise ValueError("pipeline requires at least one stage")
    if len(stages) > LED_COUNT:
        raise ValueError(f"pipeline supports at most {LED_COUNT} stages")

    base_color = parse_hex_color(spec.get("base_color"), 0x020304)
    current_color = parse_hex_color(spec.get("current_color"), 0xFFFFFF)
    attention_color = parse_hex_color(spec.get("attention_color"), 0xFFE08A)
    pulse_period = float(spec.get("pulse_period", 1.2))

    return WidgetBuildResult(
        widget_id="pipeline",
        mode="pipeline",
        payload={"stages": [asdict(stage) for stage in stages]},
        visual=dynamic_frame(_render(stages, base_color, current_color, attention_color, pulse_period), exclusive=False),
        background_visual=solid(base_color),
        background_mode="solid",
    )
