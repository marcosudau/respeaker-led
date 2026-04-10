from __future__ import annotations

from tools.effect_packager import build_parser, main
from tests.package_test_utils import write_effect_set_source


def test_packager_parser_includes_supported_commands():
    parser = build_parser()

    pack_effect = parser.parse_args(["pack-effect", "src_dir", "out.lefx"])
    pack_set = parser.parse_args(["pack-effect-set", "src_dir", "out.lefxset"])
    inspect_args = parser.parse_args(["inspect-effect-package", "demo.lefx"])
    verify_args = parser.parse_args(["verify-effect-package", "demo.lefxset"])

    assert pack_effect.command_kind == "pack_effect"
    assert pack_set.command_kind == "pack_effect_set"
    assert inspect_args.command_kind == "inspect"
    assert verify_args.command_kind == "verify"


def test_packager_tool_can_build_and_verify_effect_set(tmp_path):
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
                "layer_name": "MAIN_LAYER",
            }
        ],
        commands={
            "listening": {
                "kind": "state_toggle",
                "on": {
                    "effect": "app.voice_assistant::listening_blue",
                    "target_layer": "MAIN_LAYER",
                    "params": {},
                },
                "off": {
                    "action": "clear_layer",
                    "target_layer": "MAIN_LAYER",
                },
            }
        },
    )
    output_path = tmp_path / "voice_assistant.lefxset"

    assert main(["pack-effect-set", str(set_dir), str(output_path)]) == 0
    assert output_path.exists()
    assert main(["inspect-effect-package", str(output_path)]) == 0
    assert main(["verify-effect-package", str(output_path)]) == 0
