from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.engine.effect_registry as effect_registry_module
from src.core.models import LED_COUNT
from src.engine.effect_package_builder import build_effect_set
from src.infrastructure.paths import DEFAULT_EFFECT_SET_PATH
from src.services.service import ControllerService
from tests.package_test_utils import write_effect_set_source


class RecordingAdapter:
    def __init__(self) -> None:
        self.frames = []
        self.closed = False

    def apply_frame(self, frame):
        self.frames.append(list(frame.leds))

    def close(self):
        self.closed = True


def _startable_service(**kwargs) -> ControllerService:
    return ControllerService(
        use_device=False,
        adapter_factory=RecordingAdapter,
        signal_on_s=0.0,
        signal_off_s=0.0,
        **kwargs,
    )


def test_service_falls_back_to_preview_and_starts_worker_when_adapter_init_fails():
    def broken_adapter():
        raise RuntimeError("device missing")

    service = ControllerService(use_device=True, adapter_factory=broken_adapter)

    assert service.snapshot()["output_mode"] == "console-preview"
    assert service.snapshot()["fallback_active"] is True
    assert "device missing" in service.snapshot()["last_error"]

    service.start()
    try:
        assert service.snapshot()["render_loop_running"] is True
    finally:
        service.stop()


def test_service_applies_and_persists_default_background_fallback(tmp_path):
    state_file = tmp_path / "background_state.json"
    service = ControllerService(use_device=False, background_state_file=state_file)

    snapshot = service.snapshot()

    assert snapshot["render_layers"]["state_visual"]["effect_id"] == "solid_color"
    assert snapshot["render_layers"]["state_visual"]["params"] == {"color": "#FFFFFF", "brightness": 0.2}
    assert json.loads(state_file.read_text(encoding="utf-8"))["effect_id"] == "solid_color"


def test_service_starts_with_published_default_effect_artifact():
    assert DEFAULT_EFFECT_SET_PATH.is_file()

    service = _startable_service()
    try:
        service.start()
        default_source = next(source for source in service.list_effect_sources() if source["source_id"] == "default-effects")

        assert service.snapshot()["render_loop_running"] is True
        assert default_source["kind"] == "effect_set"
        assert Path(default_source["path"]) == DEFAULT_EFFECT_SET_PATH.resolve()
    finally:
        service.stop()


def test_service_requires_published_default_effect_artifact(monkeypatch):
    monkeypatch.setattr(effect_registry_module, "_default_effect_artifact_candidates", lambda: [])

    with pytest.raises(FileNotFoundError, match="Default effect set artifact not found"):
        _startable_service()


def test_service_restores_persisted_background_state_on_start(tmp_path):
    state_file = tmp_path / "background_state.json"
    first = ControllerService(use_device=False, background_state_file=state_file)
    try:
        first.apply_effect("solid_color", "background", {"color": "0x224466", "brightness": 0.5})
    finally:
        first.stop()

    second = ControllerService(use_device=False, background_state_file=state_file)
    try:
        snapshot = second.snapshot()
        assert snapshot["render_layers"]["state_visual"]["effect_id"] == "solid_color"
        assert snapshot["render_layers"]["state_visual"]["params"] == {"color": "0x224466", "brightness": 0.5}
    finally:
        second.stop()


def test_shutdown_does_not_overwrite_persisted_background_with_service_state(tmp_path):
    state_file = tmp_path / "background_state.json"
    first = ControllerService(use_device=False, background_state_file=state_file)
    try:
        first.apply_effect("solid_color", "background", {"color": "0x123456"})
        first.shutdown()
    finally:
        first.stop()

    second = ControllerService(use_device=False, background_state_file=state_file)
    try:
        snapshot = second.snapshot()
        assert snapshot["render_layers"]["state_visual"]["params"]["color"] == "0x123456"
    finally:
        second.stop()


def test_service_emits_start_and_stop_signal_sequences():
    adapter = RecordingAdapter()
    service = ControllerService(
        use_device=False,
        adapter_factory=lambda: adapter,
        signal_on_s=0.0,
        signal_off_s=0.0,
    )

    service.start()
    service.stop()

    green = [0x00FF00] * LED_COUNT
    red = [0xFF0000] * LED_COUNT
    black = [0] * LED_COUNT

    assert adapter.frames[:6] == [green, black, green, black, green, black]
    assert adapter.frames[-6:] == [red, black, red, black, red, black]
    assert adapter.closed is True


def test_service_can_register_and_toggle_packaged_command(tmp_path):
    set_dir = tmp_path / "voice_assistant_src"
    write_effect_set_source(
        set_dir,
        source_id="app.voice_assistant",
        set_id="voice_assistant",
        title="Voice Assistant",
        effects=[
            {
                "dir_name": "listening",
                "package_id": "voice.listening",
                "class_name": "ListeningBlueEffect",
                "effect_id": "listening_blue",
                "layer_name": "MAIN_LAYER",
                "presets": {
                    "effect_listening_default": {
                        "category": "effect",
                        "target_layer": "MAIN_LAYER",
                        "params": {"color": "#224466"},
                    }
                },
                "commands": {
                    "listening": {
                        "kind": "state_toggle",
                        "on": {"preset": "effect_listening_default"},
                        "off": {
                            "action": "clear_layer",
                            "target_layer": "MAIN_LAYER",
                        },
                    }
                },
            }
        ],
    )
    package_path = tmp_path / "voice_assistant.lefxset"
    build_effect_set(set_dir, package_path)

    service = ControllerService(use_device=False)
    try:
        registration = service.register_effect_source(str(package_path))
        assert registration["source"]["source_id"] == "app.voice_assistant"
        assert service.list_effect_commands("app.voice_assistant")[0]["command_name"] == "listening"
        assert service.list_effect_presets("app.voice_assistant", "listening_blue")[0]["preset_id"] == "effect_listening_default"

        enabled = service.invoke_effect_command("app.voice_assistant", "listening")
        assert enabled["active_visual"]["visual"]["effect_id"] == "app.voice_assistant::listening_blue"

        disabled = service.invoke_effect_command("app.voice_assistant", "listening")
        assert disabled["active_visual"] is None

        applied_preset = service.apply_effect_preset("app.voice_assistant", "effect_listening_default")
        assert applied_preset["active_effect_preset_id"] == "app.voice_assistant::effect_listening_default"
        assert applied_preset["active_visual"]["visual"]["effect_id"] == "app.voice_assistant::listening_blue"
    finally:
        service.stop()
