from __future__ import annotations

import pytest

from respeaker_led.core.models import LED_COUNT, LayerVisual, Scene, Visual
from respeaker_led.engine.renderer import SceneRenderer, render_visual_to_pixels


def _dynamic_visual(colors, *, exclusive: bool = False) -> Visual:
    return Visual("dynamic_frame", {"provider": lambda now, values=list(colors): list(values)}, exclusive=exclusive)


def render_visual(visual: Visual, *, now: float = 0.25):
    scene = Scene(timestamp=now, layers=[LayerVisual(name="test", priority=100, visual=visual)])
    return SceneRenderer().render(scene)


def test_renderer_renders_dynamic_frame_visual_from_provider():
    colors = [0x0F0F0F if index % 2 == 0 else None for index in range(LED_COUNT)]

    frame = render_visual(_dynamic_visual(colors))

    assert len(frame.leds) == LED_COUNT
    assert frame.leds[0] == 0x0F0F0F
    assert frame.leds[1] == 0
    assert frame.leds[10] == 0x0F0F0F
    assert frame.leds[11] == 0


def test_renderer_rejects_invalid_dynamic_frame_length():
    with pytest.raises(ValueError, match=f"{LED_COUNT} colors"):
        render_visual_to_pixels(_dynamic_visual([0x123456]), 0.0)


def test_renderer_blends_nonexclusive_layers_and_respects_exclusive_layers():
    base = _dynamic_visual([0x010101] * LED_COUNT)
    overlay = _dynamic_visual([0xABCDEF if index < 3 else None for index in range(LED_COUNT)])
    scene = Scene(
        timestamp=0.0,
        layers=[
            LayerVisual(name="base", priority=10, visual=base),
            LayerVisual(name="overlay", priority=20, visual=overlay),
        ],
    )

    frame = SceneRenderer().render(scene)

    assert frame.leds[:3] == [0xABCDEF] * 3
    assert frame.leds[3:] == [0x010101] * (LED_COUNT - 3)

    exclusive_scene = Scene(
        timestamp=0.0,
        layers=[
            LayerVisual(name="base", priority=10, visual=base),
            LayerVisual(name="overlay", priority=20, visual=_dynamic_visual([0xABCDEF if index < 3 else None for index in range(LED_COUNT)], exclusive=True)),
        ],
    )

    exclusive_frame = SceneRenderer().render(exclusive_scene)

    assert exclusive_frame.leds[:3] == [0xABCDEF] * 3
    assert exclusive_frame.leds[3:] == [0] * (LED_COUNT - 3)


def test_renderer_rejects_unsupported_visual_types():
    with pytest.raises(ValueError, match="Unsupported visual type"):
        render_visual_to_pixels(Visual("solid", {"color": 0x123456}), 0.0)
