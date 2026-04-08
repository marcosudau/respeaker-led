from __future__ import annotations

from urllib import error

import pytest

from src.client import ClientCallResult, LocalControllerClient


def test_client_is_best_effort_when_service_is_unavailable(monkeypatch):
    def fake_urlopen(*args, **kwargs):
        raise error.URLError("unavailable")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = LocalControllerClient(best_effort=True)
    result = client.ping()

    assert result.ok is False
    assert "unavailable" in result.error


def test_client_raises_when_best_effort_is_disabled(monkeypatch):
    def fake_urlopen(*args, **kwargs):
        raise error.URLError("unavailable")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = LocalControllerClient(best_effort=False)

    with pytest.raises(RuntimeError):
        client.ping()


def test_client_maps_countdown_command_to_expected_path(monkeypatch):
    recorded: list[tuple[str, str, dict | None]] = []

    def fake_request(self, method: str, path: str, payload=None):
        recorded.append((method, path, payload))
        return ClientCallResult(ok=True, status_code=200, data={"ok": True})

    monkeypatch.setattr(LocalControllerClient, "_request_json", fake_request)

    client = LocalControllerClient()
    result = client.start_timeout_countdown(5000, 1200, follow_up_state="transcribing", payload={"source": "stt"})

    assert result.ok is True
    assert recorded == [
        (
            "POST",
            "/api/v1/commands/start_timeout_countdown",
            {
                "total_ms": 5000,
                "remaining_ms": 1200,
                "follow_up_state": "transcribing",
                "payload": {"source": "stt"},
            },
        )
    ]