from __future__ import annotations

import json

from src.color_math import scale_color
from src.effects import solid
from src.models import LED_COUNT
from src.preset_loader import PresetRegistry
from src.runtime import ControllerRuntime


class SilentAdapter:
    def __init__(self):
        self.last_frame = None

    def apply_frame(self, frame):
        self.last_frame = frame

    def close(self):
        return None


def make_controller(registry: PresetRegistry | None = None) -> ControllerRuntime:
    return ControllerRuntime(adapter=SilentAdapter(), preset_registry=registry)


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


def test_controller_can_apply_preset_from_registry(tmp_path):
    pack_dir = tmp_path / "progress_pack"
    pack_dir.mkdir()
    (pack_dir / "preset.yaml").write_text(
        "\n".join(
            [
                "id: sample_progress",
                "name: Sample Progress",
                "description: A simple progress preset",
                "command: sample-progress",
                "sample_spec: sample.json",
            ]
        ),
        encoding="utf-8",
    )
    (pack_dir / "sample.json").write_text(json.dumps({"value": 75, "color": "0x224466"}), encoding="utf-8")
    (pack_dir / "preset.py").write_text(
        "\n".join(
            [
                "from src.effects import progress, solid",
                "from src.models import PresetBuildResult",
                "from src.spec_utils import parse_hex_color",
                "",
                "def build_preset(spec):",
                "    value = float(spec.get('value', 0))",
                "    color = parse_hex_color(spec.get('color', '0x3399FF'))",
                "    return PresetBuildResult(",
                "        preset_id='sample_progress',",
                "        mode='progress',",
                "        payload={'value': value},",
                "        visual=progress(value, color=color, base_color=0x010101),",
                "        state_visual=solid(0x010101),",
                "        state_mode='solid',",
                "    )",
            ]
        ),
        encoding="utf-8",
    )

    registry = PresetRegistry.discover(tmp_path)
    controller = make_controller(registry)
    controller.apply_preset_from_file("sample_progress", pack_dir / "sample.json")

    scene, frame = controller.render_once(now=1.0)

    assert scene.layers[0].name == "state_layer"
    assert scene.layers[1].name == "active_visual:sample_progress"
    assert controller.get_status(now=1.0)["active_preset_id"] == "sample_progress"
    assert frame.leds[0] == 0x224466
