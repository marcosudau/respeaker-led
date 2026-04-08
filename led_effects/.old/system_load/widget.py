from __future__ import annotations

from dataclasses import asdict, dataclass

from led_effects.quick_actions_layer.visuals import ring_frame, solid
from respeaker_led_controller.color_math import scale_color
from respeaker_led_controller.models import WidgetBuildResult
from respeaker_led_controller.spec_utils import parse_hex_color


RESOURCE_COLORS = {
    "cpu": 0x3A86FF,
    "ram": 0xFFD166,
    "gpu": 0xFF4D9D,
    "net": 0x06D6A0,
}


@dataclass(slots=True)
class SystemLoadSpec:
    cpu: float
    ram: float
    gpu: float
    net: float | None = None
    base_color: str | int = "0x010101"


def build_widget(spec: dict) -> WidgetBuildResult:
    load_spec = SystemLoadSpec(**spec)
    base_color = parse_hex_color(load_spec.base_color, 0x010101)
    colors = [base_color] * 12
    metrics = [
        ("cpu", load_spec.cpu, 0),
        ("ram", load_spec.ram, 3),
        ("gpu", load_spec.gpu, 6),
    ]
    if load_spec.net is not None:
        metrics.append(("net", load_spec.net, 9))

    for key, value, start in metrics:
        factor = max(0.1, min(1.0, float(value) / 100.0))
        color = scale_color(RESOURCE_COLORS[key], factor)
        colors[start % 12] = color
        if value >= 85.0:
            colors[(start + 1) % 12] = RESOURCE_COLORS[key]

    return WidgetBuildResult(
        widget_id="system_load",
        mode="system_load",
        payload={"system_load": asdict(load_spec)},
        visual=ring_frame(colors, exclusive=False),
        background_visual=solid(base_color),
        background_mode="solid",
    )
