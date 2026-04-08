from __future__ import annotations

import pytest

from src.cli import build_parser, use_real_device
from src.preset_loader import PresetRegistry


def test_parser_includes_service_and_state_commands():
    parser = build_parser(PresetRegistry.empty())

    parsed = parser.parse_args(["serve", "--host", "127.0.0.1", "--port", "9999"])

    assert parsed.command_kind == "serve"
    assert parsed.host == "127.0.0.1"
    assert parsed.port == 9999


def test_parser_includes_countdown_and_remote_control_commands():
    parser = build_parser(PresetRegistry.empty())

    parsed = parser.parse_args(["start-countdown", "5000", "--remaining-ms", "1500", "--follow-up-state", "transcribing"])

    assert parsed.command_kind == "start_countdown"
    assert parsed.total_ms == 5000
    assert parsed.remaining_ms == 1500
    assert parsed.follow_up_state == "transcribing"


def test_no_device_flag_switches_to_console_preview():
    parser = build_parser(PresetRegistry.empty())

    parsed = parser.parse_args(["--no-device", "demo", "--seconds", "1"])

    assert use_real_device(parsed) is False


def test_removed_legacy_widget_commands_are_not_wired():
    parser = build_parser(PresetRegistry.empty())

    with pytest.raises(SystemExit):
        parser.parse_args(["list-widgets"])

    with pytest.raises(SystemExit):
        parser.parse_args(["project-agents"])

    with pytest.raises(SystemExit):
        parser.parse_args(["serve-api"])

    with pytest.raises(SystemExit):
        parser.parse_args(["push-event"])
