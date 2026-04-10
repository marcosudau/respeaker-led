from __future__ import annotations

import json
import textwrap

import pytest

from src.engine.effect_command_registry import parse_command_definitions
from src.engine.effect_package_builder import build_effect_package, build_effect_set
from src.engine.effect_package_loader import inspect_effect_source, load_effect_package, load_effect_set, verify_effect_source


def _write_effect_source(root, *, package_id: str, source_id: str, class_name: str, effect_id: str, color: str = "0x224466"):
    root.mkdir(parents=True, exist_ok=True)
    (root / "effect.yaml").write_text(
        "\n".join(
            [
                f"package_id: {package_id}",
                f"source_id: {source_id}",
                f"entry_class: {class_name}",
                "min_service_version: 1.0.0",
            ]
        ),
        encoding="utf-8",
    )
    (root / "effect.py").write_text(
        textwrap.dedent(
            f"""
            from src.core.effect_schema import BaseEffect, EffectDefinition, LayerId, LayerRule, PlaybackMode, EffectCapabilities, RenderContext


            class {class_name}(BaseEffect):
                definition = EffectDefinition(
                    id="{effect_id}",
                    title="{class_name}",
                    description="Generated for tests",
                    defaults={{"color": "{color}"}},
                    capabilities=EffectCapabilities(
                        playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                        restorable=True,
                    ),
                    layer_rules={{
                        LayerId.MAIN_LAYER: LayerRule(
                            allowed=True,
                            allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                        ),
                    }},
                )

                def render(self, ctx: RenderContext) -> list[int | None]:
                    return [int(ctx.params.get("color", "{color}"), 16)] * ctx.led_count
            """
        ),
        encoding="utf-8",
    )


def test_parse_command_definitions_requires_commands_mapping():
    with pytest.raises(ValueError, match="non-empty 'commands' object"):
        parse_command_definitions("app.voice_assistant", {})


def test_build_and_load_effect_package_roundtrip(tmp_path):
    source_dir = tmp_path / "effect_src"
    output_path = tmp_path / "listening.lefx"
    _write_effect_source(
        source_dir,
        package_id="voice.listening",
        source_id="app.voice_assistant",
        class_name="ListeningBlueEffect",
        effect_id="listening_blue",
    )

    built = build_effect_package(source_dir, output_path)

    assert built.kind == "effect_package"
    loaded = load_effect_package(output_path)
    inspected = inspect_effect_source(output_path)
    verified = verify_effect_source(output_path)

    assert loaded.manifest.qualified_effect_id == "app.voice_assistant::listening_blue"
    assert loaded.effect_class.__name__ == "ListeningBlueEffect"
    assert inspected["kind"] == "effect_package"
    assert inspected["qualified_effect_id"] == "app.voice_assistant::listening_blue"
    assert verified.ok is True
    assert verified.effect_ids == ("app.voice_assistant::listening_blue",)


def test_build_and_load_effect_set_roundtrip(tmp_path):
    set_dir = tmp_path / "voice_assistant"
    effects_root = set_dir / "effects"
    idle_dir = effects_root / "idle"
    listening_dir = effects_root / "listening"
    _write_effect_source(
        idle_dir,
        package_id="voice.idle",
        source_id="app.voice_assistant",
        class_name="IdleBlueEffect",
        effect_id="idle_blue",
        color="0x112233",
    )
    _write_effect_source(
        listening_dir,
        package_id="voice.listening",
        source_id="app.voice_assistant",
        class_name="ListeningBlueEffect",
        effect_id="listening_blue",
        color="0x224466",
    )
    set_dir.mkdir(parents=True, exist_ok=True)
    (set_dir / "set.yaml").write_text(
        "\n".join(
            [
                "set_id: voice_assistant",
                "source_id: app.voice_assistant",
                "title: Voice Assistant",
                "version: 1",
                "min_service_version: 1.0.0",
                "effects:",
                "  - idle",
                "  - listening",
            ]
        ),
        encoding="utf-8",
    )
    (set_dir / "commands.json").write_text(
        json.dumps(
            {
                "commands": {
                    "idle": {
                        "kind": "state_toggle",
                        "on": {
                            "effect": "app.voice_assistant::idle_blue",
                            "target_layer": "STATE_LAYER",
                            "params": {},
                        },
                        "off": {
                            "action": "clear_layer",
                            "target_layer": "STATE_LAYER",
                        },
                    },
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
                    },
                }
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "voice_assistant.lefxset"
    built = build_effect_set(set_dir, output_path)
    loaded = load_effect_set(output_path)
    inspected = inspect_effect_source(output_path)
    verified = verify_effect_source(output_path)

    assert built.kind == "effect_set"
    assert loaded.manifest.source_id == "app.voice_assistant"
    assert [item.manifest.effect_id for item in loaded.effects] == ["idle_blue", "listening_blue"]
    assert [command.command_name for command in loaded.commands] == ["idle", "listening"]
    assert inspected["kind"] == "effect_set"
    assert inspected["commands"] == ["idle", "listening"]
    assert verified.ok is True
    assert verified.command_names == ("idle", "listening")
