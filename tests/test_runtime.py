from __future__ import annotations

import json

from src.core.color_math import scale_color
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
    assert any(layer.name == "state:primary:recording" for layer in scene.layers)
    assert any(color != 0 for color in frame.leds)


def test_runtime_rejects_removed_main_layer_name():
    controller = make_controller()
    controller.set_state("idle", timestamp=0.0)
    import pytest

    from src.core.effect_schema import parse_layer_id

    with pytest.raises(ValueError, match="Unknown layer"):
        parse_layer_id("main")


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
    assert frame.leds[4] == scale_color(0x00C066, 0.5)

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


def test_runtime_applies_default_background_fallback_as_dim_white():
    controller = make_controller()
    controller.apply_default_background_state()

    _, frame = controller.render_once(now=0.0)

    assert frame.leds == [0x333333] * LED_COUNT


def test_controller_can_apply_effect_and_clear_runtime_layer():
    controller = make_controller()
    controller.set_state_target("solid_color", {"color": "0x224466"}, timestamp=0.0)

    scene, frame = controller.render_once(now=0.0)

    assert any(layer.name == "state:primary" for layer in scene.layers)
    assert controller.get_status(now=0.0)["render_layers"]["state_visual"]["effect_id"] == "solid_color"
    assert frame.leds[0] == 0x224466

    controller.clear_state_target()
    controller.render_once(now=0.1)

    assert controller.get_status(now=0.1)["render_layers"]["state_visual"] is None


def test_runtime_separates_overlay_config_and_runtime_inputs():
    controller = make_controller()
    controller.set_overlay(
        "progress_bar",
        "progress",
        {"color": "#112233", "background_color": "#010101"},
        {"value": "50%"},
        timestamp=0.0,
    )

    status = controller.get_status(now=0.0)
    visual = status["render_layers"]["direction_visual"]

    assert visual["params"]["background_color"] == "#010101"
    assert visual["inputs"]["progress"] == 50.0


def test_push_overlay_heartbeat_keeps_last_value_for_three_windows():
    controller = make_controller()
    controller.set_overlay(
        "progress_bar",
        "progress",
        {"color": "#112233", "background_color": "#010101"},
        {"progress": 50},
        timestamp=0.0,
    )

    _, healthy_frame = controller.render_once(now=2.999)
    healthy = controller.get_status(now=2.999)["render_layers"]["direction_visual"]

    assert healthy["input_health"]["status"] == "healthy"
    assert healthy_frame.leds[:6] == [0x112233] * 6

    _, failed_frame = controller.render_once(now=3.0)
    failed = controller.get_status(now=3.0)["render_layers"]["direction_visual"]

    assert failed["input_health"]["status"] == "failed"
    assert failed["input_health"]["missed_heartbeats"] == 3
    assert failed_frame.leds == [0x010101] * LED_COUNT

    controller.update_overlay("progress", {}, timestamp=3.1)
    _, recovered_frame = controller.render_once(now=3.1)
    recovered = controller.get_status(now=3.1)["render_layers"]["direction_visual"]

    assert recovered["input_health"]["status"] == "healthy"
    assert recovered_frame.leds[:6] == [0x112233] * 6


def test_off_is_idempotent_and_does_not_clear_a_different_target():
    controller = make_controller()
    controller.set_state_target("solid_color", {"color": "blau"})
    controller.set_state_target("soft_pulse", action="off")
    controller.set_overlay("progress_bar", "shared", inputs={"value": 25})
    controller.set_overlay("direction_indicator", "shared", action="off")

    status = controller.get_status()

    assert status["render_layers"]["state_visual"]["effect_id"] == "solid_color"
    assert status["render_layers"]["direction_visual"]["effect_id"] == "progress_bar"


def test_timed_overlay_needs_no_channel_and_cannot_toggle():
    import pytest

    controller = make_controller()
    invocation = controller.set_overlay("countdown_circle", config={"total_ms": "1s"})

    assert invocation.target_layer is LayerId.TEMP_OVERLAY_LAYER
    assert invocation.requested_duration_ms == 1000
    with pytest.raises(ValueError, match="only action 'on'"):
        controller.set_overlay("countdown_circle", action="toggle")

