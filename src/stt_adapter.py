from __future__ import annotations

from typing import Any

from .client import LocalControllerClient


class SttLedAdapter:
    def __init__(self, client: LocalControllerClient | Any) -> None:
        self.client = client

    def on_vad_detect_start(self, payload: dict | None = None):
        return self.client.set_state("listening", payload or {})

    def on_recording_start(self, payload: dict | None = None):
        return self.client.set_state("recording", payload or {})

    def on_turn_detection_start(
        self,
        total_ms: int,
        remaining_ms: int | None = None,
        *,
        follow_up_state: str | None = "transcribing",
        payload: dict | None = None,
    ):
        return self.client.start_timeout_countdown(
            total_ms,
            remaining_ms,
            follow_up_state=follow_up_state,
            payload=payload or {},
        )

    def on_turn_detection_stop(self, payload: dict | None = None):
        self.client.cancel_timeout_countdown()
        return self.client.set_state("recording", payload or {})

    def on_recording_stop(self, payload: dict | None = None):
        return self.client.set_state("transcribing", payload or {})

    def on_transcription_start(self, payload: dict | None = None):
        return self.client.set_state("transcribing", payload or {})

    def on_text_committed(self, *, text_length: int | None = None, payload: dict | None = None):
        event_payload = dict(payload or {})
        if text_length is not None:
            event_payload["text_length"] = text_length
        self.client.emit_event("text_committed", event_payload)
        return self.client.set_state("idle", payload or {})

    def on_wakeword_detection_start(self, payload: dict | None = None):
        return self.client.set_state("wakeword_armed", payload or {})

    def on_wakeword_detected(self, payload: dict | None = None):
        self.client.emit_event("wakeword_ack", payload or {})
        return self.client.set_state("listening", payload or {})

    def on_wakeword_detection_end(self, payload: dict | None = None):
        return self.client.set_state("idle", payload or {})