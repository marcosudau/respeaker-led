from __future__ import annotations

from src.effects import blink, dynamic_frame, progress, pulse, ring_frame, segments, solid, visual_from_spec
from src.models import LED_COUNT, LayerVisual, Scene
from src.renderer import SceneRenderer


def render_visual(visual, *, now: float = 0.25):
    scene = Scene(timestamp=now, layers=[LayerVisual(name="test", priority=100, visual=visual)])
    return SceneRenderer().render(scene)


def test_effect_helpers_build_valid_visual_data():
    visuals = [
        solid(0x123456),
        pulse(0x204060, base_color=0x102030, period=2.0),
        blink(0xFF0000, base_color=0x010101, period=1.0, duty_cycle=0.5),
        progress(50, color=0x112233, base_color=0x010101),
        segments([{"start": 1, "end": 3, "color": 0xABCDEF}]),
        ring_frame([index for index in range(LED_COUNT)]),
        dynamic_frame(lambda now: [0x0F0F0F if index % 2 == 0 else None for index in range(LED_COUNT)]),
    ]

    assert all(visual.type for visual in visuals)
    assert visual_from_spec({"type": "solid", "params": {"color": 0x123456}, "exclusive": False}).type == "solid"


def test_renderer_renders_solid_visual_to_full_ring_frame():
    frame = render_visual(solid(0x123456))

    assert len(frame.leds) == LED_COUNT
    assert frame.leds == [0x123456] * LED_COUNT


def test_renderer_renders_pulse_visual_to_valid_frame():
    frame = render_visual(pulse(0x204060, base_color=0x102030, period=2.0), now=0.5)

    assert len(frame.leds) == LED_COUNT
    assert all(isinstance(color, int) for color in frame.leds)
    assert all(0x102030 != color for color in frame.leds)


def test_renderer_renders_blink_visual_for_on_and_off_phase():
    on_frame = render_visual(blink(0xFF0000, base_color=0x010101, period=1.0, duty_cycle=0.5), now=0.1)
    off_frame = render_visual(blink(0xFF0000, base_color=0x010101, period=1.0, duty_cycle=0.5), now=0.8)

    assert len(on_frame.leds) == LED_COUNT
    assert on_frame.leds == [0xFF0000] * LED_COUNT
    assert off_frame.leds == [0x010101] * LED_COUNT


def test_renderer_renders_progress_visual_with_expected_split():
    frame = render_visual(progress(50, color=0x112233, base_color=0x010101))

    assert len(frame.leds) == LED_COUNT
    assert frame.leds[:6] == [0x112233] * 6
    assert frame.leds[6:] == [0x010101] * 6


def test_renderer_renders_segments_visual_with_sparse_leds():
    frame = render_visual(segments([{"start": 1, "end": 3, "color": 0xABCDEF}]))

    assert len(frame.leds) == LED_COUNT
    assert frame.leds[0] == 0
    assert frame.leds[1:4] == [0xABCDEF] * 3
    assert frame.leds[4] == 0


def test_renderer_renders_ring_frame_visual_exactly():
    colors = [index * 0x010101 for index in range(LED_COUNT)]
    frame = render_visual(ring_frame(colors))

    assert len(frame.leds) == LED_COUNT
    assert frame.leds == colors


def test_renderer_renders_dynamic_frame_visual_from_provider():
    frame = render_visual(dynamic_frame(lambda now: [0x0F0F0F if index % 2 == 0 else None for index in range(LED_COUNT)]))

    assert len(frame.leds) == LED_COUNT
    assert frame.leds[0] == 0x0F0F0F
    assert frame.leds[1] == 0
    assert frame.leds[10] == 0x0F0F0F
    assert frame.leds[11] == 0
