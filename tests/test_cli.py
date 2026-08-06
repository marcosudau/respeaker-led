from __future__ import annotations

import pytest

from respeaker_led.interfaces.cli import _normalize_argv, build_parser, use_real_device


def test_parser_includes_service_controls():
    parser = build_parser()
    parsed = parser.parse_args(
        ["serve", "--host", "127.0.0.1", "--port", "9999", "--port-pool", "9999,10000-10001"]
    )

    assert parsed.command_kind == "serve"
    assert parsed.port == 9999
    assert parsed.port_pool == "9999,10000-10001"


def test_parser_uses_small_verb_first_effect_vocabulary():
    parser = build_parser()

    listed = parser.parse_args(["list", "states", "--details"])
    shown = parser.parse_args(["show", "default-effects::solid_color"])
    state = parser.parse_args(["set", "state", "solid_color", "--off"])
    shorthand = parser.parse_args(
        ["set", "progress_bar", "--channel", "volume", "--inputs", '{"value": 50}']
    )
    updated = parser.parse_args(["update", "volume", "--inputs", '{"value": 75}'])
    cleared = parser.parse_args(["clear", "overlay", "volume"])
    clear_shorthand = parser.parse_args(["clear", "volume"])
    emitted = parser.parse_args(["emit", "warning_flash"])

    assert listed.command_kind == "list_v2"
    assert listed.details is True
    assert shown.command_kind == "show_v2"
    assert state.action == "off"
    assert shorthand.subject_or_target == "progress_bar"
    assert updated.command_kind == "update_v2"
    assert cleared.command_kind == "clear_v2"
    assert clear_shorthand.subject == "volume"
    assert emitted.command_kind == "emit_v2"


def test_parser_includes_effect_source_management():
    parser = build_parser()
    parsed = parser.parse_args(
        ["register-effect-source", "C:/tmp/voice.lefxset", "--enabled", "false"]
    )

    assert parsed.command_kind == "register_effect_source"
    assert parsed.enabled is False


def test_slash_switches_normalize_to_long_options():
    assert _normalize_argv(["set", "solid_color", "/off"]) == [
        "set",
        "solid_color",
        "--off",
    ]
    assert _normalize_argv(["list", "state", "/json"]) == [
        "list",
        "state",
        "--json",
    ]


def test_no_device_flag_switches_to_console_preview():
    parsed = build_parser().parse_args(["--no-device", "serve"])
    assert use_real_device(parsed) is False


def test_removed_v1_effect_commands_are_not_wired():
    parser = build_parser()
    for command in (
        ["apply-effect", "solid_color", "main"],
        ["clear-layer", "main"],
        ["list-commands"],
        ["invoke-command", "pkg", "name"],
        ["apply-effect-preset", "pkg::preset"],
    ):
        with pytest.raises(SystemExit):
            parser.parse_args(command)
