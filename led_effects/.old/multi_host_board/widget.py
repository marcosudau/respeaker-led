from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from led_effects.quick_actions_layer.visuals import dynamic_frame, solid
from respeaker_led_controller.color_math import blend, scale_color, segment_lengths
from respeaker_led_controller.models import LED_COUNT, WidgetBuildResult
from respeaker_led_controller.spec_utils import parse_hex_color


ROLE_COLORS = {
    "pc": 0x3A86FF,
    "server": 0x00C853,
    "nas": 0xFFB703,
    "container": 0x9B5DE5,
    "agent": 0x00AEEF,
}

STATE_COLORS = {
    "ok": 0x00C853,
    "busy": 0x00AEEF,
    "warning": 0xFFB703,
    "degraded": 0xFB5607,
    "offline": 0xD90429,
}


@dataclass(slots=True)
class HostStatus:
    name: str
    role: str
    state: str
    load: float = 0.0
    is_primary: bool = False
    needs_attention: bool = False
    unread_alerts: int = 0


def _render(hosts: list[HostStatus], base_color: int, primary_color: int, alert_color: int, pulse_period: float):
    def provider(now: float) -> list[int | None]:
        frame: list[int | None] = [base_color] * LED_COUNT
        cursor = 0
        for host, length in zip(hosts, segment_lengths(len(hosts))):
            role_color = ROLE_COLORS.get(host.role.lower(), 0x3A86FF)
            state_color = STATE_COLORS.get(host.state.lower(), 0xFFFFFF)
            start = cursor
            end = cursor + length - 1
            cursor += length

            load = max(0.0, min(100.0, float(host.load)))
            segment_base = blend(base_color, role_color, 0.12 + (load / 100.0) * 0.18)
            for index in range(start, end + 1):
                frame[index] = segment_base

            anchor = blend(role_color, state_color, 0.45)
            if host.is_primary:
                phase = (math.sin((now / pulse_period) * 2.0 * math.pi) + 1.0) / 2.0
                anchor = blend(anchor, primary_color, phase * 0.6)
            elif host.state.lower() in {"offline", "degraded"}:
                phase = (now % 0.9) / 0.9
                anchor = state_color if phase < 0.55 else scale_color(state_color, 0.25)
            frame[start] = anchor

            if length > 1:
                tail_index = end
                if host.needs_attention or max(0, int(host.unread_alerts)) > 0:
                    phase = (now % 0.8) / 0.8
                    frame[tail_index] = alert_color if phase < 0.45 else state_color
                else:
                    frame[tail_index] = blend(segment_base, state_color, load / 100.0)
        return frame

    return provider


def build_widget(spec: dict) -> WidgetBuildResult:
    raw_hosts = spec.get("hosts", [])
    hosts = [HostStatus(**item) for item in raw_hosts]
    if not hosts:
        raise ValueError("multi_host_board requires at least one host")
    if len(hosts) > LED_COUNT:
        raise ValueError(f"multi_host_board supports at most {LED_COUNT} hosts")

    base_color = parse_hex_color(spec.get("base_color"), 0x020304)
    primary_color = parse_hex_color(spec.get("primary_color"), 0xFFFFFF)
    alert_color = parse_hex_color(spec.get("alert_color"), 0xFFE08A)
    pulse_period = float(spec.get("pulse_period", 1.5))

    return WidgetBuildResult(
        widget_id="multi_host_board",
        mode="multi_host_board",
        payload={"hosts": [asdict(host) for host in hosts]},
        visual=dynamic_frame(_render(hosts, base_color, primary_color, alert_color, pulse_period), exclusive=False),
        background_visual=solid(base_color),
        background_mode="solid",
    )
