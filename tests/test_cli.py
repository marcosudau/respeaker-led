from __future__ import annotations

import pytest

from src.cli import _normalize_argv, build_parser, use_real_device


def test_parser_includes_service_and_state_commands():
    parser = build_parser()

    parsed = parser.parse_args(["serve", "--host", "127.0.0.1", "--port", "9999", "--port-pool", "9999,10000-10001"])

    assert parsed.command_kind == "serve"
    assert parsed.host == "127.0.0.1"
    assert parsed.port == 9999
    assert parsed.port_pool == "9999,10000-10001"


def test_parser_includes_countdown_and_remote_control_commands():
    parser = build_parser()

    parsed = parser.parse_args(["start-countdown", "5000", "--remaining-ms", "1500", "--follow-up-state", "transcribing"])

    assert parsed.command_kind == "start_countdown"
    assert parsed.total_ms == 5000
    assert parsed.remaining_ms == 1500
    assert parsed.follow_up_state == "transcribing"


def test_parser_includes_effect_and_layer_commands():
    parser = build_parser()

    list_parsed = parser.parse_args(["list-effects", "--host", "127.0.0.1"])
    apply_parsed = parser.parse_args(
        [
            "apply-effect",
            "solid_color",
            "main",
            "--params",
            '{"color": "0x224466"}',
            "--duration-ms",
            "900",
            "--priority",
            "650",
            "--enqueue",
            "--replace-existing",
            "false",
        ]
    )
    clear_parsed = parser.parse_args(["clear-layer", "main_layer"])

    assert list_parsed.command_kind == "list_effects"
    assert apply_parsed.command_kind == "apply_effect"
    assert apply_parsed.effect_id == "solid_color"
    assert apply_parsed.target_layer == "main"
    assert apply_parsed.duration_ms == 900
    assert apply_parsed.priority == 650
    assert apply_parsed.enqueue is True
    assert apply_parsed.replace_existing is False
    assert clear_parsed.command_kind == "clear_layer"


def test_no_device_flag_switches_to_console_preview():
    parser = build_parser()

    parsed = parser.parse_args(["--no-device", "serve", "--host", "127.0.0.1"])

    assert use_real_device(parsed) is False


def test_normalize_argv_accepts_serve_compatibility_spellings():
    assert _normalize_argv(["--serve", "--port", "8891"]) == ["serve", "--port", "8891"]
    assert _normalize_argv(["--no-device", "--serve", "--port", "8891"]) == ["--no-device", "serve", "--port", "8891"]
    assert _normalize_argv(["--", "serve", "--port", "8891"]) == ["serve", "--port", "8891"]


def test_removed_local_demo_and_legacy_widget_commands_are_not_wired():
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["list-widgets"])

    with pytest.raises(SystemExit):
        parser.parse_args(["project-agents"])

    with pytest.raises(SystemExit):
        parser.parse_args(["serve-api"])

    with pytest.raises(SystemExit):
        parser.parse_args(["push-event"])

    with pytest.raises(SystemExit):
        parser.parse_args(["demo"])

    with pytest.raises(SystemExit):
        parser.parse_args(["list-standard-effects"])

    with pytest.raises(SystemExit):
        parser.parse_args(["showcase"])
