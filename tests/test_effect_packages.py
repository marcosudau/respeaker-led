from __future__ import annotations

import json
import textwrap

import pytest

from src.engine.effect_command_registry import parse_command_definitions
from src.engine.effect_package_builder import (
    build_effect_package,
    build_effect_set,
    init_effect_batch,
    init_effect_set_source,
    init_effect_source,
    validate_effect_set_source,
    validate_effect_source,
)
from src.engine.effect_package_loader import inspect_effect_source, load_effect_package, load_effect_set, verify_effect_source


def _write_effect_source(
    root,
    *,
    package_id: str,
    source_id: str,
    class_name: str,
    effect_id: str,
    color: str = "0x224466",
    layer_name: str = "MAIN_LAYER",
    presets: dict | None = None,
    commands: dict | None = None,
):
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
            from src.core.effect_schema import BaseEffect, EffectDefinition, EffectParamDefinition, LayerId, LayerRule, PlaybackMode, EffectCapabilities, RenderContext


            class {class_name}(BaseEffect):
                definition = EffectDefinition(
                    id="{effect_id}",
                    title="{class_name}",
                    description="Generated for tests",
                    parameter_schema={{
                        "color": EffectParamDefinition(name="color", type="color", default="{color}"),
                    }},
                    defaults={{"color": "{color}"}},
                    capabilities=EffectCapabilities(
                        playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                        restorable=True,
                    ),
                    layer_rules={{
                        LayerId.{layer_name}: LayerRule(
                            allowed=True,
                            allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                        ),
                    }},
                )

                def render(self, ctx: RenderContext) -> list[int | None]:
                    return [int(str(ctx.params.get("color", "{color}")).replace("#", "0x"), 16)] * ctx.led_count
            """
        ),
        encoding="utf-8",
    )
    if presets is not None:
        (root / "presets.yaml").write_text(
            _dump_simple_yaml({"presets": presets}),
            encoding="utf-8",
        )
    if commands is not None:
        (root / "commands.json").write_text(
            json.dumps({"commands": commands}, ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def _dump_simple_yaml(payload: dict) -> str:
    lines: list[str] = []

    def _render(value, indent: int, key: str | None = None) -> None:
        prefix = " " * indent
        if isinstance(value, dict):
            if key is not None:
                lines.append(f"{prefix}{key}:")
                indent += 2
                prefix = " " * indent
            for nested_key, nested_value in value.items():
                _render(nested_value, indent, str(nested_key))
            return
        if isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                lines.append(f"{prefix}  - {json.dumps(item) if isinstance(item, str) and '#' in item else item}")
            return
        rendered = json.dumps(value) if isinstance(value, str) and ("#" in value or ":" in value) else value
        lines.append(f"{prefix}{key}: {rendered}")

    for payload_key, payload_value in payload.items():
        _render(payload_value, 0, str(payload_key))
    return "\n".join(lines) + "\n"


def test_parse_command_definitions_requires_commands_mapping():
    with pytest.raises(ValueError, match="non-empty 'commands' object"):
        parse_command_definitions("app.voice_assistant", {})


def test_build_and_load_effect_package_roundtrip_with_embedded_presets_and_commands(tmp_path):
    source_dir = tmp_path / "effect_src"
    output_path = tmp_path / "listening.lefx"
    _write_effect_source(
        source_dir,
        package_id="voice.listening",
        source_id="app.voice_assistant",
        class_name="ListeningBlueEffect",
        effect_id="listening_blue",
        presets={
            "effect_listening_default": {
                "category": "effect",
                "target_layer": "MAIN_LAYER",
                "params": {"color": "#224466"},
                "tags": ["effect"],
            }
        },
        commands={
            "effect_listening": {
                "kind": "state_toggle",
                "on": {"preset": "effect_listening_default"},
                "off": {"action": "clear_layer", "target_layer": "MAIN_LAYER"},
            }
        },
    )

    built = build_effect_package(source_dir, output_path)

    assert built.kind == "effect_package"
    loaded = load_effect_package(output_path)
    inspected = inspect_effect_source(output_path)
    verified = verify_effect_source(output_path)

    assert loaded.manifest.qualified_effect_id == "app.voice_assistant::listening_blue"
    assert loaded.effect_class.__name__ == "ListeningBlueEffect"
    assert [preset.preset_id for preset in loaded.presets] == ["effect_listening_default"]
    assert [command.command_name for command in loaded.commands] == ["effect_listening"]
    assert inspected["kind"] == "effect_package"
    assert inspected["presets"] == ["effect_listening_default"]
    assert inspected["commands"] == ["effect_listening"]
    assert verified.ok is True
    assert verified.effect_ids == ("app.voice_assistant::listening_blue",)
    assert verified.preset_ids == ("app.voice_assistant::effect_listening_default",)
    assert verified.command_names == ("effect_listening",)


def test_init_and_validate_effect_source_scaffold(tmp_path):
    target_dir = tmp_path / "idle_blue"

    scaffold = init_effect_source(
        target_dir,
        effect_id="idle_blue",
        source_id="app.voice_assistant",
        layer="STATE_LAYER",
    )

    validation = validate_effect_source(target_dir)
    output_path = tmp_path / "idle_blue.lefx"
    built = build_effect_package(target_dir, output_path)

    assert scaffold.kind == "effect_source"
    assert (target_dir / "effect.yaml").exists()
    assert (target_dir / "presets.yaml").exists()
    assert (target_dir / "commands.json").exists()
    assert (target_dir / "effect.py").exists()
    assert (target_dir / "assets").is_dir()
    assert (target_dir / "extra" / "__init__.py").exists()
    assert validation.identifier == "app.voice_assistant::idle_blue"
    assert validation.details["preset_count"] == 1
    assert validation.details["command_count"] == 1
    assert built.identifier == "app.voice_assistant::idle_blue"


def test_init_effect_batch_creates_multiple_scaffolds(tmp_path):
    batch_file = tmp_path / "batch.json"
    batch_file.write_text(
        json.dumps(
            {
                "source_id": "app.voice_assistant",
                "effects": [
                    {"effect_id": "idle_blue", "layer": "STATE_LAYER"},
                    {"effect_id": "event_ping", "title": "Event Ping", "class_name": "EventPingEffect", "layer": "EVENT_LAYER"},
                ],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    results = init_effect_batch(batch_file, tmp_path / "generated")

    assert [result.target_path.name for result in results] == ["idle_blue", "event_ping"]
    assert (tmp_path / "generated" / "idle_blue" / "presets.yaml").exists()
    assert (tmp_path / "generated" / "event_ping" / "commands.json").exists()


def test_build_and_load_effect_set_roundtrip_aggregates_embedded_presets_and_commands(tmp_path):
    set_dir = tmp_path / "voice_assistant"
    effects_root = set_dir / "effects"
    _write_effect_source(
        effects_root / "idle",
        package_id="voice.idle",
        source_id="app.voice_assistant",
        class_name="IdleBlueEffect",
        effect_id="idle_blue",
        color="0x112233",
        layer_name="STATE_LAYER",
        presets={
            "state_idle_default": {
                "category": "state",
                "target_layer": "STATE_LAYER",
                "params": {"color": "#112233"},
                "tags": ["state", "idle"],
            }
        },
        commands={
            "state_idle": {
                "kind": "state_toggle",
                "on": {"preset": "state_idle_default"},
                "off": {"action": "clear_layer", "target_layer": "STATE_LAYER"},
            }
        },
    )
    _write_effect_source(
        effects_root / "error",
        package_id="voice.error",
        source_id="app.voice_assistant",
        class_name="ErrorFlashEffect",
        effect_id="error_flash",
        color="0xFF0000",
        layer_name="EVENT_LAYER",
        presets={
            "event_error_flash": {
                "category": "event",
                "target_layer": "EVENT_LAYER",
                "params": {"color": "#FF0000"},
                "duration_ms": 250,
                "tags": ["event", "error"],
            }
        },
        commands={
            "event_error": {
                "kind": "event",
                "on": {"preset": "event_error_flash"},
            }
        },
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
                "  - error",
            ]
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
    assert [item.manifest.effect_id for item in loaded.effects] == ["idle_blue", "error_flash"]
    assert [preset.preset_id for preset in loaded.presets] == ["state_idle_default", "event_error_flash"]
    assert [command.command_name for command in loaded.commands] == ["state_idle", "event_error"]
    assert inspected["kind"] == "effect_set"
    assert inspected["presets"] == ["state_idle_default", "event_error_flash"]
    assert inspected["commands"] == ["state_idle", "event_error"]
    assert verified.ok is True
    assert verified.command_names == ("state_idle", "event_error")


def test_validate_effect_set_source_returns_transition_warning_for_source_directories(tmp_path):
    set_dir = tmp_path / "voice_assistant"
    effects_root = set_dir / "effects"
    _write_effect_source(
        effects_root / "idle",
        package_id="voice.idle",
        source_id="app.voice_assistant",
        class_name="IdleBlueEffect",
        effect_id="idle_blue",
        color="0x112233",
        layer_name="STATE_LAYER",
        presets={
            "state_idle_default": {
                "category": "state",
                "target_layer": "STATE_LAYER",
                "params": {"color": "#112233"},
            }
        },
        commands={
            "state_idle": {
                "kind": "state_toggle",
                "on": {"preset": "state_idle_default"},
                "off": {"action": "clear_layer", "target_layer": "STATE_LAYER"},
            }
        },
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
            ]
        ),
        encoding="utf-8",
    )

    validation = validate_effect_set_source(set_dir)

    assert validation.identifier == "voice_assistant"
    assert len(validation.warnings) == 1
    assert "Prefer prebuilt .lefx files" in validation.warnings[0]
    assert validation.details["preset_count"] == 1
    assert validation.details["command_count"] == 1


def test_build_effect_set_from_prebuilt_lefx_packages(tmp_path):
    effects_build = tmp_path / "built_effects"
    idle_src = tmp_path / "idle_src"
    listening_src = tmp_path / "listening_src"
    _write_effect_source(
        idle_src,
        package_id="voice.idle",
        source_id="app.voice_assistant",
        class_name="IdleBlueEffect",
        effect_id="idle_blue",
        color="0x112233",
        layer_name="STATE_LAYER",
        presets={
            "state_idle_default": {
                "category": "state",
                "target_layer": "STATE_LAYER",
                "params": {"color": "#112233"},
            }
        },
        commands={
            "state_idle": {
                "kind": "state_toggle",
                "on": {"preset": "state_idle_default"},
                "off": {"action": "clear_layer", "target_layer": "STATE_LAYER"},
            }
        },
    )
    _write_effect_source(
        listening_src,
        package_id="voice.listening",
        source_id="app.voice_assistant",
        class_name="ListeningBlueEffect",
        effect_id="listening_blue",
        color="0x224466",
        presets={
            "effect_listening_default": {
                "category": "effect",
                "target_layer": "MAIN_LAYER",
                "params": {"color": "#224466"},
            }
        },
        commands={
            "effect_listening": {
                "kind": "state_toggle",
                "on": {"preset": "effect_listening_default"},
                "off": {"action": "clear_layer", "target_layer": "MAIN_LAYER"},
            }
        },
    )
    build_effect_package(idle_src, effects_build / "idle_blue.lefx")
    build_effect_package(listening_src, effects_build / "listening_blue.lefx")

    set_dir = tmp_path / "voice_assistant_set"
    scaffold = init_effect_set_source(
        set_dir,
        set_id="voice_assistant",
        source_id="app.voice_assistant",
        title="Voice Assistant",
    )
    (set_dir / "effects" / "idle_blue.lefx").write_bytes((effects_build / "idle_blue.lefx").read_bytes())
    (set_dir / "effects" / "listening_blue.lefx").write_bytes((effects_build / "listening_blue.lefx").read_bytes())
    (set_dir / "set.yaml").write_text(
        "\n".join(
            [
                "set_id: voice_assistant",
                "source_id: app.voice_assistant",
                "title: Voice Assistant",
                "version: 1",
                "min_service_version: 1.0.0",
                "effects:",
                "  - idle_blue.lefx",
                "  - listening_blue.lefx",
            ]
        ),
        encoding="utf-8",
    )

    validation = validate_effect_set_source(set_dir)
    built = build_effect_set(set_dir, tmp_path / "voice_assistant.lefxset")
    loaded = load_effect_set(tmp_path / "voice_assistant.lefxset")

    assert scaffold.kind == "effect_set_source"
    assert validation.warnings == ()
    assert built.warnings == ()
    assert [effect.manifest.qualified_effect_id for effect in loaded.effects] == [
        "app.voice_assistant::idle_blue",
        "app.voice_assistant::listening_blue",
    ]
    assert [preset.preset_id for preset in loaded.presets] == ["state_idle_default", "effect_listening_default"]


def test_build_effect_set_rejects_mismatched_source_id_in_prebuilt_package(tmp_path):
    idle_src = tmp_path / "idle_src"
    foreign_src = tmp_path / "foreign_src"
    _write_effect_source(
        idle_src,
        package_id="voice.idle",
        source_id="app.voice_assistant",
        class_name="IdleBlueEffect",
        effect_id="idle_blue",
    )
    _write_effect_source(
        foreign_src,
        package_id="voice.foreign",
        source_id="app.other_app",
        class_name="ForeignEffect",
        effect_id="foreign_blue",
    )
    build_effect_package(idle_src, tmp_path / "idle_blue.lefx")
    build_effect_package(foreign_src, tmp_path / "foreign_blue.lefx")

    set_dir = tmp_path / "voice_assistant_set"
    init_effect_set_source(set_dir, set_id="voice_assistant", source_id="app.voice_assistant")
    (set_dir / "effects" / "idle_blue.lefx").write_bytes((tmp_path / "idle_blue.lefx").read_bytes())
    (set_dir / "effects" / "foreign_blue.lefx").write_bytes((tmp_path / "foreign_blue.lefx").read_bytes())
    (set_dir / "set.yaml").write_text(
        "\n".join(
            [
                "set_id: voice_assistant",
                "source_id: app.voice_assistant",
                "title: Voice Assistant",
                "version: 1",
                "min_service_version: 1.0.0",
                "effects:",
                "  - idle_blue.lefx",
                "  - foreign_blue.lefx",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="expected 'app.voice_assistant'"):
        build_effect_set(set_dir, tmp_path / "voice_assistant.lefxset")


def test_build_effect_package_rejects_invalid_embedded_preset_category_prefix(tmp_path):
    source_dir = tmp_path / "effect_src"
    _write_effect_source(
        source_dir,
        package_id="voice.listening",
        source_id="app.voice_assistant",
        class_name="ListeningBlueEffect",
        effect_id="listening_blue",
        presets={
            "idle_default": {
                "category": "state",
                "target_layer": "STATE_LAYER",
                "params": {"color": "#224466"},
            }
        },
    )

    with pytest.raises(ValueError, match="must use the 'state_' prefix"):
        validate_effect_source(source_dir)


def test_build_effect_package_rejects_command_referencing_unknown_preset(tmp_path):
    source_dir = tmp_path / "effect_src"
    _write_effect_source(
        source_dir,
        package_id="voice.listening",
        source_id="app.voice_assistant",
        class_name="ListeningBlueEffect",
        effect_id="listening_blue",
        commands={
            "effect_listening": {
                "kind": "state_toggle",
                "on": {"preset": "effect_missing"},
                "off": {"action": "clear_layer", "target_layer": "MAIN_LAYER"},
            }
        },
    )

    with pytest.raises(ValueError, match="unknown preset"):
        validate_effect_source(source_dir)
