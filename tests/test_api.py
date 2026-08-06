from __future__ import annotations

import json

from fastapi.testclient import TestClient

from respeaker_led.integrations.adapters import MemoryFrameAdapter
from respeaker_led.engine.effect_package_builder import build_effect_set
from respeaker_led.interfaces.api import create_app
from tests.package_test_utils import write_effect_set_source


def make_client() -> TestClient:
    app = create_app(fps=12.0, use_device=False, adapter_factory=MemoryFrameAdapter)
    return TestClient(app)


def test_api_root_health_ping_and_status_snapshot():
    with make_client() as client:
        root_response = client.get("/")
        assert root_response.status_code == 200
        assert root_response.json()["api_base"] == "/api/v2"
        assert root_response.json()["commands"] == ["list", "show", "set", "clear", "update", "emit"]
        assert root_response.json()["output_mode"] == "console-preview"

        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["render_loop_running"] is True

        ping_response = client.get("/api/v1/ping")
        assert ping_response.status_code == 200
        assert ping_response.json()["ok"] is True

        status_response = client.get("/api/v1/status")
        assert status_response.status_code == 200
        payload = status_response.json()
        assert payload["base_state"]["name"] == "idle"
        assert "event_overlay" in payload
        assert "render_count" in payload
        assert payload["render_loop_running"] is True


def test_api_lists_builtin_effects_and_can_apply_and_clear_effects():
    with make_client() as client:
        list_response = client.get("/api/v2/states")
        assert list_response.status_code == 200
        assert "solid_color" in list_response.json()

        apply_response = client.post(
            "/api/v2/set/state",
            json={
                "target": "solid_color",
                "config": {"color": "blau"},
            },
        )
        assert apply_response.status_code == 200
        state_visual = apply_response.json()["status"]["render_layers"]["state_visual"]
        assert state_visual["effect_id"] == "solid_color"
        assert state_visual["params"]["color"] == "#0000FF"

        clear_response = client.post(
            "/api/v2/clear/state",
            json={"slot": "primary"},
        )
        assert clear_response.status_code == 200
        assert clear_response.json()["status"]["render_layers"]["state_visual"] is None

        show_response = client.get("/api/v2/show/progress_bar")
        assert show_response.status_code == 200
        detail = show_response.json()
        assert detail["visual"]["color_model"] == "mono"
        assert detail["visual"]["composition"] == "transparent"
        assert detail["runtime_inputs"]["progress"]["aliases"] == ["value"]
        assert detail["input_sampling"] == {
            "mode": "push",
            "provider_id": None,
            "interval_ms": 0,
            "heartbeat_interval_ms": 1000,
            "max_missed_heartbeats": 3,
            "failure_after_ms": 3000,
        }


def test_api_generic_command_flow():
    with make_client() as client:
        state_response = client.post(
            "/api/v2/set/state",
            json={"target": "soft_pulse", "config": {"color": "gruen"}},
        )
        assert state_response.status_code == 200
        assert state_response.json()["status"]["render_layers"]["state_visual"]["effect_id"] == "soft_pulse"

        event_response = client.post(
            "/api/v2/emit/event",
            json={"target": "warning_flash", "config": {"color": "rot"}},
        )
        assert event_response.status_code == 200
        assert event_response.json()["status"]["event_overlay"]["current"]["name"] == "warning_flash"

        overlay_response = client.post(
            "/api/v2/set/overlay",
            json={"target": "progress_bar", "channel": "volume", "inputs": {"value": "25%"}},
        )
        assert overlay_response.status_code == 200

        update_response = client.post(
            "/api/v2/update/overlay",
            json={"channel": "volume", "inputs": {"value": 75}},
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"]["render_layers"]["direction_visual"]["inputs"]["progress"] == 75.0

        clear_response = client.post(
            "/api/v2/clear/overlay",
            json={"channel": "volume"},
        )
        assert clear_response.status_code == 200
        assert clear_response.json()["status"]["render_layers"]["direction_visual"] is None


def test_api_apply_effect_returns_404_for_unknown_effect():
    with make_client() as client:
        response = client.post(
            "/api/v2/set/state",
            json={"target": "not_real", "config": {}},
        )

        assert response.status_code == 404


def test_api_can_register_list_and_set_packaged_preset(tmp_path):
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
                "layer_name": "STATE_LAYER",
                "presets": {
                    "listening_default": {
                        "params": {"color": "#224466"},
                    }
                },
            }
        ],
    )
    package_path = tmp_path / "voice_assistant.lefxset"
    build_effect_set(set_dir, package_path)

    with make_client() as client:
        register_response = client.post(
            "/api/v1/effect-sources/register",
            json={"path": str(package_path), "enabled": True},
        )
        assert register_response.status_code == 200

        sources_response = client.get("/api/v1/effect-sources")
        assert sources_response.status_code == 200
        assert any(item["source_id"] == "app.voice_assistant" for item in sources_response.json()["items"])

        effect_response = client.get("/api/v1/effects/app.voice_assistant/listening_blue")
        assert effect_response.status_code == 200
        assert effect_response.json()["qualified_id"] == "app.voice_assistant::listening_blue"

        presets_response = client.get("/api/v1/effects/app.voice_assistant/listening_blue/presets")
        assert presets_response.status_code == 200
        assert presets_response.json()["items"][0]["preset_id"] == "listening_default"

        on_response = client.post(
            "/api/v2/set/state",
            json={"target": "app.voice_assistant::listening_default"},
        )
        assert on_response.status_code == 200
        assert on_response.json()["status"]["render_layers"]["state_visual"]["effect_id"] == "app.voice_assistant::listening_blue"

        off_response = client.post(
            "/api/v2/set/state",
            json={"target": "app.voice_assistant::listening_default", "action": "off"},
        )
        assert off_response.status_code == 200
        assert off_response.json()["status"]["render_layers"]["state_visual"] is None
