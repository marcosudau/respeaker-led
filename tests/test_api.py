from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.adapters import MemoryFrameAdapter
from src.api import create_app
from src.preset_loader import PresetRegistry


def make_client(registry: PresetRegistry | None = None) -> TestClient:
    app = create_app(fps=12.0, use_device=False, adapter_factory=MemoryFrameAdapter, preset_registry=registry)
    return TestClient(app)


def test_api_root_health_ping_and_status_snapshot():
    with make_client() as client:
        root_response = client.get("/")
        assert root_response.status_code == 200
        assert root_response.json()["api_base"] == "/api/v1"
        assert "set_state" in root_response.json()["commands"]
        assert "apply_effect" in root_response.json()["commands"]
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
        list_response = client.get("/api/v1/effects")
        assert list_response.status_code == 200
        effect_ids = {item["id"] for item in list_response.json()["items"]}
        assert {"solid_color", "soft_pulse", "warning_flash"}.issubset(effect_ids)

        apply_response = client.post(
            "/api/v1/commands/apply_effect",
            json={
                "effect_id": "solid_color",
                "target_layer": "main",
                "params": {"color": "0x224466"},
            },
        )
        assert apply_response.status_code == 200
        assert apply_response.json()["active_visual"]["visual"]["effect_id"] == "solid_color"
        assert apply_response.json()["active_visual"]["payload"]["color"] == "0x224466"

        clear_response = client.post(
            "/api/v1/commands/clear_layer",
            json={"target_layer": "main_layer"},
        )
        assert clear_response.status_code == 200
        assert clear_response.json()["active_visual"] is None


def test_api_generic_command_flow():
    with make_client() as client:
        state_response = client.post(
            "/api/v1/commands/set_state",
            json={"state_name": "recording", "payload": {"source": "manual"}},
        )
        assert state_response.status_code == 200
        assert state_response.json()["base_state"]["name"] == "recording"

        event_response = client.post(
            "/api/v1/commands/emit_event",
            json={"event_name": "trigger_received", "payload": {"event_id": "api-event", "duration_ms": 500}},
        )
        assert event_response.status_code == 200
        assert event_response.json()["event_overlay"]["current"]["id"] == "api-event"

        countdown_response = client.post(
            "/api/v1/commands/start_timeout_countdown",
            json={"total_ms": 5000, "remaining_ms": 1500, "follow_up_state": "transcribing"},
        )
        assert countdown_response.status_code == 200
        assert countdown_response.json()["countdown"]["follow_up_state"] == "transcribing"

        direction_response = client.post(
            "/api/v1/commands/set_direction",
            json={"direction_deg": 120.0},
        )
        assert direction_response.status_code == 200
        assert direction_response.json()["direction_deg"] == 120.0

        brightness_response = client.post(
            "/api/v1/commands/set_brightness",
            json={"level": 0.5},
        )
        assert brightness_response.status_code == 200
        assert brightness_response.json()["brightness"] == 0.5

        enabled_response = client.post(
            "/api/v1/commands/set_enabled",
            json={"enabled": False},
        )
        assert enabled_response.status_code == 200
        assert enabled_response.json()["enabled"] is False
        assert enabled_response.json()["last_frame"]["leds"] == [0] * 12

        clear_direction_response = client.post("/api/v1/commands/clear_direction")
        assert clear_direction_response.status_code == 200
        assert clear_direction_response.json()["direction_deg"] is None

        cancel_countdown_response = client.post("/api/v1/commands/cancel_timeout_countdown")
        assert cancel_countdown_response.status_code == 200
        assert cancel_countdown_response.json()["countdown"] is None

        reset_response = client.post("/api/v1/commands/reset")
        assert reset_response.status_code == 200
        assert reset_response.json()["base_state"]["name"] == "idle"
        assert reset_response.json()["enabled"] is True


def test_api_apply_effect_returns_404_for_unknown_effect():
    with make_client() as client:
        response = client.post(
            "/api/v1/commands/apply_effect",
            json={"effect_id": "not_real", "target_layer": "main_layer", "params": {}},
        )

        assert response.status_code == 404


def test_preset_routes_are_defined_even_without_discovered_presets():
    with make_client() as client:
        list_response = client.get("/api/v1/presets")
        assert list_response.status_code == 200
        assert list_response.json() == {"items": []}

        detail_response = client.get("/api/v1/presets/not-real")
        assert detail_response.status_code == 404


def test_preset_activation_endpoint_works_with_discovered_pack(tmp_path):
    pack_dir = tmp_path / "demo_pack"
    pack_dir.mkdir()
    (pack_dir / "preset.yaml").write_text(
        "\n".join(
            [
                "id: demo",
                "name: Demo Preset",
                "description: Demo preset for API tests",
                "command: demo-preset",
                "sample_spec: sample.json",
            ]
        ),
        encoding="utf-8",
    )
    (pack_dir / "sample.json").write_text(json.dumps({"color": "0x112233"}), encoding="utf-8")
    (pack_dir / "preset.py").write_text(
        "\n".join(
            [
                "from src.effects import solid",
                "from src.models import PresetBuildResult",
                "from src.spec_utils import parse_hex_color",
                "",
                "def build_preset(spec):",
                "    color = parse_hex_color(spec.get('color', '0x112233'))",
                "    return PresetBuildResult(",
                "        preset_id='demo',",
                "        mode='solid',",
                "        payload={'color': color},",
                "        visual=solid(color),",
                "    )",
            ]
        ),
        encoding="utf-8",
    )
    registry = PresetRegistry.discover(tmp_path)

    with make_client(registry) as client:
        sample_response = client.get("/api/v1/presets/demo/sample")
        assert sample_response.status_code == 200

        activate_response = client.post("/api/v1/presets/demo/activate", json={"spec": {"color": "0x112233"}})
        assert activate_response.status_code == 200
        assert activate_response.json()["active_visual"]["id"] == "demo"
        assert activate_response.json()["active_preset_id"] == "demo"

        assert client.post("/api/v1/main-layer/progress", json={"value": 62}).status_code == 404
        assert client.put("/api/v1/state-layer/visual", json={}).status_code == 404
