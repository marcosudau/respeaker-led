from __future__ import annotations

from urllib import error

import pytest

from respeaker_led.interfaces.client import ClientCallResult, LocalControllerClient


def test_client_is_best_effort_when_service_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(error.URLError("unavailable")),
    )
    result = LocalControllerClient(best_effort=True).ping()

    assert result.ok is False
    assert "unavailable" in result.error


def test_client_raises_when_best_effort_is_disabled(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(error.URLError("unavailable")),
    )

    with pytest.raises(RuntimeError):
        LocalControllerClient(best_effort=False).ping()


def test_client_maps_v2_reads_and_mutations(monkeypatch):
    recorded: list[tuple[str, str, dict | None]] = []

    def fake_request(self, method: str, path: str, payload=None):
        recorded.append((method, path, payload))
        return ClientCallResult(ok=True, status_code=200, data={"ok": True})

    monkeypatch.setattr(LocalControllerClient, "_request_json", fake_request)
    client = LocalControllerClient()

    client.list_v2("state")
    client.list_v2("overlay", details=True)
    client.show_target("default-effects::solid_color")
    client.set_state_target("solid_color", {"color": "blau"}, action="toggle")
    client.set_overlay_target(
        "progress_bar",
        "volume",
        {"color": "gruen"},
        {"value": "25%"},
    )
    client.update_overlay_target("volume", {"value": 75})
    client.clear_overlay_target("volume")
    client.emit_event_target("warning_flash", {"color": "rot"}, priority=700)

    assert recorded == [
        ("GET", "/api/v2/states", None),
        ("GET", "/api/v2/overlays?details=true", None),
        ("GET", "/api/v2/show/default-effects%3A%3Asolid_color", None),
        (
            "POST",
            "/api/v2/set/state",
            {
                "target": "solid_color",
                "config": {"color": "blau"},
                "slot": "primary",
                "action": "toggle",
            },
        ),
        (
            "POST",
            "/api/v2/set/overlay",
            {
                "target": "progress_bar",
                "channel": "volume",
                "config": {"color": "gruen"},
                "inputs": {"value": "25%"},
                "action": "on",
            },
        ),
        ("POST", "/api/v2/update/overlay", {"channel": "volume", "inputs": {"value": 75}}),
        ("POST", "/api/v2/clear/overlay", {"channel": "volume"}),
        (
            "POST",
            "/api/v2/emit/event",
            {"target": "warning_flash", "config": {"color": "rot"}, "priority": 700},
        ),
    ]


def test_client_maps_effect_source_management(monkeypatch):
    recorded: list[tuple[str, str, dict | None]] = []

    def fake_request(self, method: str, path: str, payload=None):
        recorded.append((method, path, payload))
        return ClientCallResult(ok=True, status_code=200, data={"ok": True})

    monkeypatch.setattr(LocalControllerClient, "_request_json", fake_request)
    client = LocalControllerClient()
    client.list_effect_sources()
    client.register_effect_source("C:/tmp/demo.lefxset", enabled=False)

    assert recorded == [
        ("GET", "/api/v1/effect-sources", None),
        (
            "POST",
            "/api/v1/effect-sources/register",
            {"path": "C:/tmp/demo.lefxset", "enabled": False},
        ),
    ]
