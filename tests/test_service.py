from __future__ import annotations

import json

from src.core.models import LED_COUNT
from src.services.service import ControllerService


class RecordingAdapter:
    def __init__(self) -> None:
        self.frames = []
        self.closed = False

    def apply_frame(self, frame):
        self.frames.append(list(frame.leds))

    def close(self):
        self.closed = True


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