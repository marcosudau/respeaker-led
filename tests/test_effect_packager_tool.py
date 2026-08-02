from __future__ import annotations

import json

from tools.effect_packager import build_parser, main
from tests.package_test_utils import write_effect_set_source


def test_packager_parser_includes_supported_commands():
    parser = build_parser()

    init_effect = parser.parse_args([
        "init-effect",
        "target_dir",
        "--effect-id",
        "idle_blue",
        "--source-id",
        "app.voice_assistant",
    ])
    init_set = parser.parse_args([
        "init-effect-set",
        "target_dir",
        "--set-id",
        "voice_assistant",
        "--source-id",
        "app.voice_assistant",
    ])
    init_batch = parser.parse_args(["init-effect-batch", "batch.json", "generated"])
    validate_effect = parser.parse_args(["validate-effect-source", "src_dir"])
    validate_set = parser.parse_args(["validate-effect-set-source", "src_dir"])
    pack_effect = parser.parse_args(["pack-effect", "src_dir", "out.lefx"])
    pack_set = parser.parse_args(["pack-effect-set", "src_dir", "out.lefxset"])
    inspect_args = parser.parse_args(["inspect-effect-package", "demo.lefx"])
    verify_args = parser.parse_args(["verify-effect-package", "demo.lefxset"])

    assert init_effect.command_kind == "init_effect"
    assert init_set.command_kind == "init_effect_set"
    assert init_batch.command_kind == "init_effect_batch"
    assert validate_effect.command_kind == "validate_effect_source"
    assert validate_set.command_kind == "validate_effect_set_source"
    assert pack_effect.command_kind == "pack_effect"
    assert pack_set.command_kind == "pack_effect_set"
    assert inspect_args.command_kind == "inspect"
    assert verify_args.command_kind == "verify"


def test_packager_tool_can_scaffold_validate_build_and_verify_effect_set(tmp_path, capsys):
    batch_file = tmp_path / "batch.json"
    batch_file.write_text(
        json.dumps(
            {
                "source_id": "app.voice_assistant",
                "effects": [
                    {"effect_id": "idle_blue", "definition_type": "state"},
                    {
                        "effect_id": "listening_blue",
                        "definition_type": "overlay",
                        "overlay_mode": "controlled",
                    },
                ],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    generated_root = tmp_path / "generated_effects"

    assert main(["init-effect-batch", str(batch_file), str(generated_root)]) == 0
    batch_payload = json.loads(capsys.readouterr().out)
    assert batch_payload["count"] == 2

    idle_src = generated_root / "idle_blue"
    idle_package = tmp_path / "idle_blue.lefx"
    assert main(["validate-effect-source", str(idle_src)]) == 0
    validate_payload = json.loads(capsys.readouterr().out)
    assert validate_payload["identifier"] == "app.voice_assistant::idle_blue"
    assert main(["pack-effect", str(idle_src), str(idle_package)]) == 0
    pack_payload = json.loads(capsys.readouterr().out)
    assert pack_payload["warnings"] == []

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
    generated_set = tmp_path / "generated_set"
    assert main([
        "init-effect-set",
        str(generated_set),
        "--set-id",
        "generated_set",
        "--source-id",
        "app.voice_assistant",
    ]) == 0
    init_set_payload = json.loads(capsys.readouterr().out)
    assert init_set_payload["kind"] == "effect_set_source"
    assert "commands.json" not in " ".join(init_set_payload["created_files"])

    output_path = tmp_path / "voice_assistant.lefxset"

    assert main(["validate-effect-set-source", str(set_dir)]) == 0
    validate_set_payload = json.loads(capsys.readouterr().out)
    assert "warnings" in validate_set_payload
    assert main(["pack-effect-set", str(set_dir), str(output_path)]) == 0
    pack_set_payload = json.loads(capsys.readouterr().out)
    assert pack_set_payload["kind"] == "effect_set"
    assert output_path.exists()
    assert main(["inspect-effect-package", str(output_path)]) == 0
    inspect_payload = json.loads(capsys.readouterr().out)
    assert inspect_payload["kind"] == "effect_set"
    assert main(["verify-effect-package", str(output_path)]) == 0
    verify_payload = json.loads(capsys.readouterr().out)
    assert verify_payload["ok"] is True
