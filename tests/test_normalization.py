from __future__ import annotations

from respeaker_led.engine.effect_registry import build_default_effect_registry
from respeaker_led.core.effect_schema import CommandKind, LayerId, PlaybackMode
from respeaker_led.integrations.application_commands import ControllerCommandNormalizer, build_effect_invocation


def test_set_state_normalization_maps_recording_to_background_and_state_invocations():
    normalizer = ControllerCommandNormalizer()
    registry = build_default_effect_registry()
    commands = normalizer.normalize_set_state("recording", {"source": "manual"}, timestamp=1.5)

    assert [command.kind for command in commands] == [CommandKind.SET_EFFECT, CommandKind.SET_EFFECT]
    assert commands[0].target_layer is LayerId.BACKGROUND_STATE_LAYER
    assert commands[0].effect_id == "solid_color"
    assert commands[1].target_layer is LayerId.STATE_LAYER
    assert commands[1].effect_id == "soft_pulse"

    invocation = build_effect_invocation(commands[1], registry, invocation_id="recording-1", created_at=1.5)

    assert invocation.playback_mode is PlaybackMode.PERSISTENT
    assert invocation.params["speed"] == 1800 / 1100
    assert invocation.params["background_color"] == 0x031108
    assert "base_color" not in invocation.params
    assert invocation.params["__scene_name"] == "state:primary:recording"


def test_clear_state_normalization_clears_state_layer_and_restores_idle_background():
    normalizer = ControllerCommandNormalizer()
    commands = normalizer.normalize_clear_state(timestamp=2.0)

    assert commands[0].target_layer is LayerId.BACKGROUND_STATE_LAYER
    assert commands[0].effect_id == "solid_color"
    assert commands[1].kind is CommandKind.CLEAR_LAYER
    assert commands[1].target_layer is LayerId.STATE_LAYER


def test_emit_event_normalization_produces_single_run_event_invocation():
    normalizer = ControllerCommandNormalizer()
    registry = build_default_effect_registry()
    commands = normalizer.normalize_emit_event(
        "warning",
        {"event_id": "warn-1", "duration_ms": 1200},
        timestamp=3.0,
    )

    assert len(commands) == 1
    assert commands[0].target_layer is LayerId.EVENT_LAYER
    assert commands[0].enqueue is True
    assert commands[0].effect_id == "warning_flash"

    invocation = build_effect_invocation(commands[0], registry, invocation_id="warn-1", created_at=3.0)

    assert invocation.playback_mode is PlaybackMode.SINGLE_RUN
    assert invocation.requested_duration_ms == 1200
    assert invocation.priority == 600
    assert invocation.params["background_color"] == 0x1A1005
    assert "base_color" not in invocation.params


def test_direction_normalization_targets_ongoing_overlay_layer():
    normalizer = ControllerCommandNormalizer()
    commands = normalizer.normalize_set_direction(120.0, timestamp=4.0)

    assert len(commands) == 1
    assert commands[0].target_layer is LayerId.ONGOING_OVERLAY_LAYER
    assert commands[0].effect_id == "direction_indicator"
    assert commands[0].inputs["direction_deg"] == 120.0
    assert "direction_deg" not in commands[0].params
