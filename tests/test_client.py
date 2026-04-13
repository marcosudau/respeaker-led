from __future__ import annotations

from urllib import error

import pytest

from src.interfaces.client import ClientCallResult, LocalControllerClient


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


def test_client_maps_apply_effect_and_clear_layer_commands(monkeypatch):
    recorded: list[tuple[str, str, dict | None]] = []

    def fake_request(self, method: str, path: str, payload=None):
        recorded.append((method, path, payload))
        return ClientCallResult(ok=True, status_code=200, data={"ok": True})

    monkeypatch.setattr(LocalControllerClient, "_request_json", fake_request)

    client = LocalControllerClient()
    apply_result = client.apply_effect(
        "solid_color",
        "main",
        {"color": "0x224466"},
        duration_ms=900,
        priority=700,
        enqueue=True,
        replace_existing=False,
    )
    clear_result = client.clear_layer("main_layer")

    assert apply_result.ok is True
    assert clear_result.ok is True
    assert recorded == [
        (
            "POST",
            "/api/v1/commands/apply_effect",
            {
                "effect_id": "solid_color",
                "target_layer": "main",
                "params": {"color": "0x224466"},
                "duration_ms": 900,
                "priority": 700,
                "enqueue": True,
                "replace_existing": False,
            },
        ),
        (
            "POST",
            "/api/v1/commands/clear_layer",
            {"target_layer": "main_layer"},
        ),
    ]


def test_client_maps_set_direction_command(monkeypatch):
    recorded: list[tuple[str, str, dict | None]] = []

    def fake_request(self, method: str, path: str, payload=None):
        recorded.append((method, path, payload))
        return ClientCallResult(ok=True, status_code=200, data={"ok": True})

    monkeypatch.setattr(LocalControllerClient, "_request_json", fake_request)

    client = LocalControllerClient()
    result = client.set_direction(120.0)

    assert result.ok is True
    assert recorded == [
        (
            "POST",
            "/api/v1/commands/set_direction",
            {"direction": 120.0},
        )
    ]


def test_client_maps_effect_source_and_packaged_command_requests(monkeypatch):
    recorded: list[tuple[str, str, dict | None]] = []

    def fake_request(self, method: str, path: str, payload=None):
        recorded.append((method, path, payload))
        return ClientCallResult(ok=True, status_code=200, data={"ok": True})

    monkeypatch.setattr(LocalControllerClient, "_request_json", fake_request)

    client = LocalControllerClient()
    assert client.list_effect_sources().ok is True
    assert client.register_effect_source("C:/tmp/demo.lefxset", enabled=False).ok is True
    assert client.list_commands("app.voice_assistant").ok is True
    assert client.invoke_command("app.voice_assistant", "listening", "off").ok is True

    assert recorded == [
        ("GET", "/api/v1/effect-sources", None),
        ("POST", "/api/v1/effect-sources/register", {"path": "C:/tmp/demo.lefxset", "enabled": False}),
        ("GET", "/api/v1/commands/app.voice_assistant", None),
        ("POST", "/api/v1/commands/app.voice_assistant/listening/off", None),
    ]


def test_client_maps_effect_metadata_and_preset_requests(monkeypatch):
    recorded: list[tuple[str, str, dict | None]] = []

    def fake_request(self, method: str, path: str, payload=None):
        recorded.append((method, path, payload))
        return ClientCallResult(ok=True, status_code=200, data={"ok": True})

    monkeypatch.setattr(LocalControllerClient, "_request_json", fake_request)

    client = LocalControllerClient()
    assert client.get_effect("app.voice_assistant", "idle_blue").ok is True
    assert client.list_effect_presets("app.voice_assistant", "idle_blue").ok is True
    assert client.list_effect_commands_for_effect("app.voice_assistant", "idle_blue").ok is True
    assert client.get_effect_preset("app.voice_assistant", "state_idle_default").ok is True
    assert client.apply_effect_preset("app.voice_assistant", "state_idle_default").ok is True
    assert client.apply_effect_for_source("app.voice_assistant", "idle_blue", "state_layer", {"color": "#112233"}).ok is True

    assert recorded == [
        ("GET", "/api/v1/effects/app.voice_assistant/idle_blue", None),
        ("GET", "/api/v1/effects/app.voice_assistant/idle_blue/presets", None),
        ("GET", "/api/v1/effects/app.voice_assistant/idle_blue/commands", None),
        ("GET", "/api/v1/effect-presets/app.voice_assistant/state_idle_default", None),
        ("POST", "/api/v1/effect-presets/app.voice_assistant/state_idle_default/apply", None),
        (
            "POST",
            "/api/v1/effects/app.voice_assistant/idle_blue/apply",
            {
                "target_layer": "state_layer",
                "params": {"color": "#112233"},
                "duration_ms": None,
                "priority": None,
                "enqueue": False,
                "replace_existing": True,
            },
        ),
    ]
