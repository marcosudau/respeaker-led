from __future__ import annotations

import json

from src.core.color_math import scale_color
from src.engine.effects import solid
from src.core.effect_schema import LayerId
from src.core.models import LED_COUNT
from src.engine.runtime import ControllerRuntime


class SilentAdapter:
    def __init__(self):
        self.last_frame = None

    def apply_frame(self, frame):
        self.last_frame = frame

    def close(self):
        return None


def make_controller() -> ControllerRuntime:
    return ControllerRuntime(adapter=SilentAdapter())


def test_render_once_produces_frame_and_stores_last_scene_and_frame():
    controller = make_controller()
    controller.set_state("recording", timestamp=0.0)

    scene, frame = controller.render_once(now=0.5)

    assert scene is controller.last_scene
    assert frame is controller.last_frame
    assert controller.adapter.last_frame is frame
    assert len(frame.leds) == LED_COUNT
    assert any(layer.name == "state_layer" for layer in scene.layers)
    assert any(layer.name == "active_visual:base-state:recording" for layer in scene.layers)
    assert any(color != 0 for color in frame.leds)


def test_render_once_marks_invalid_active_visual_with_diagnostic_overlay():
    controller = make_controller()
    controller.set_state("idle", timestamp=0.0)
    controller.set_active_visual(
        layer_id="broken",
        mode="manual",
        visual=solid(0x020202),
        valid=False,
    )

    scene, frame = controller.render_once(now=0.0)

    assert "active-visual-invalid" in scene.diagnostics
    assert frame.leds[0] == 0xFFFFFF


def test_countdown_lifecycle_restores_state_and_applies_follow_up_state():
    controller = make_controller()
    controller.set_state("recording", timestamp=0.0)
    controller.start_timeout_countdown(4000, 2000, follow_up_state="transcribing", timestamp=0.0)

    scene, _ = controller.render_once(now=0.5)

    assert any(layer.name == "countdown_overlay" for layer in scene.layers)
    assert controller.get_status(now=0.5)["countdown"]["remaining_ms"] == 1500

    controller.update_timeout_countdown(200, timestamp=0.6)
    controller.render_once(now=0.81)

    assert controller.get_status(now=0.81)["countdown"] is None
    assert controller.get_status(now=0.81)["base_state"]["name"] == "transcribing"


def test_direction_brightness_and_enabled_affect_output():
    controller = make_controller()
    controller.set_state("idle", timestamp=0.0)
    controller.set_direction(120.0)
    controller.set_brightness(0.5)

    scene, frame = controller.render_once(now=1.0)

    assert any(layer.name == "direction_overlay" for layer in scene.layers)
    assert frame.leds[4] == scale_color(0xEAF8FF, 0.5)

    controller.set_enabled(False)
    _, off_frame = controller.render_once(now=1.1)

    assert off_frame.leds == [0] * LED_COUNT


def test_runtime_can_export_and_restore_persisted_background_state():
    controller = make_controller()
    controller.apply_effect(
        "solid_color",
        LayerId.BACKGROUND_STATE_LAYER,
        {"color": "#FFFFFF", "brightness": 0.2},
        timestamp=0.0,
    )

    disposition, persisted_state = controller.background_state_persistence_snapshot()

    assert disposition == "persistable"
    assert persisted_state is not None
    assert persisted_state.effect_id == "solid_color"
    assert persisted_state.params == {"color": "#FFFFFF", "brightness": 0.2}

    restored = make_controller()
    restored.restore_persisted_background_state(persisted_state)
    _, frame = restored.render_once(now=0.0)

    assert frame.leds == [0x333333] * LED_COUNT


def test_runtime_can_persist_and_restore_legacy_background_visuals():
    controller = make_controller()
    controller.set_state_visual(solid(0x112233), mode="custom")

    disposition, persisted_state = controller.background_state_persistence_snapshot()

    assert disposition == "persistable"
    assert persisted_state is not None
    assert persisted_state.effect_id == "legacy_visual"

    restored = make_controller()
    restored.restore_persisted_background_state(persisted_state)
    _, frame = restored.render_once(now=0.0)

    assert frame.leds == [0x112233] * LED_COUNT


def test_runtime_applies_default_background_fallback_as_dim_white():
    controller = make_controller()
    controller.apply_default_background_state()

    _, frame = controller.render_once(now=0.0)

    assert frame.leds == [0x333333] * LED_COUNT


def test_controller_can_apply_effect_and_clear_runtime_layer():
    controller = make_controller()
    controller.apply_effect("solid_color", LayerId.MAIN_LAYER, {"color": "0x224466"}, timestamp=0.0)

    scene, frame = controller.render_once(now=0.0)

    assert any(layer.name.startswith("active_visual:solid_color") for layer in scene.layers)
    assert controller.get_status(now=0.0)["active_visual"]["visual"]["effect_id"] == "solid_color"
    assert frame.leds[0] == 0x224466

    controller.clear_layer(LayerId.MAIN_LAYER)
    controller.render_once(now=0.1)

    assert controller.get_status(now=0.1)["active_visual"] is None

