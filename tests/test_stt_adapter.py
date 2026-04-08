from __future__ import annotations

from src.stt_adapter import SttLedAdapter


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def set_state(self, state_name: str, payload=None):
        self.calls.append(("set_state", state_name, payload or {}))

    def emit_event(self, event_name: str, payload=None):
        self.calls.append(("emit_event", event_name, payload or {}))

    def start_timeout_countdown(self, total_ms: int, remaining_ms=None, *, follow_up_state=None, payload=None):
        self.calls.append(("start_timeout_countdown", total_ms, remaining_ms, follow_up_state, payload or {}))

    def cancel_timeout_countdown(self):
        self.calls.append(("cancel_timeout_countdown",))


def test_stt_adapter_maps_core_callbacks_to_generic_led_commands():
    client = RecordingClient()
    adapter = SttLedAdapter(client)

    adapter.on_vad_detect_start()
    adapter.on_recording_start({"source": "stt"})
    adapter.on_turn_detection_start(5000, 1400, payload={"source": "stt"})
    adapter.on_turn_detection_stop()
    adapter.on_text_committed(text_length=42)

    assert client.calls == [
        ("set_state", "listening", {}),
        ("set_state", "recording", {"source": "stt"}),
        ("start_timeout_countdown", 5000, 1400, "transcribing", {"source": "stt"}),
        ("cancel_timeout_countdown",),
        ("set_state", "recording", {}),
        ("emit_event", "text_committed", {"text_length": 42}),
        ("set_state", "idle", {}),
    ]