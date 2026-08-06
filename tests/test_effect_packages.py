from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from respeaker_led.core.effect_schema import DefinitionType, OverlayMode
from respeaker_led.engine.effect_package_builder import (
    build_effect_package,
    build_effect_set,
    init_effect_batch,
    init_effect_set_source,
    init_effect_source,
    validate_effect_set_source,
    validate_effect_source,
)
from respeaker_led.engine.effect_package_loader import (
    inspect_effect_source,
    load_effect_package,
    load_effect_set,
    verify_effect_source,
)
from tests.package_test_utils import write_effect_set_source, write_effect_source


def test_build_and_load_v2_effect_package_with_config_only_preset(tmp_path):
    source = tmp_path / "source"
    write_effect_source(
        source,
        package_id="voice.listening",
        source_id="app.voice",
        class_name="ListeningEffect",
        effect_id="listening",
        layer_name="STATE_LAYER",
        presets={
            "listening_blue": {
                "params": {"color": "#224466"},
                "tags": ["blue"],
            }
        },
    )

    output = tmp_path / "listening.lefx"
    build_effect_package(source, output)
    loaded = load_effect_package(output)
    inspected = inspect_effect_source(output)
    verified = verify_effect_source(output)

    assert loaded.manifest.format == "lefx/2"
    assert loaded.manifest.definition_type is DefinitionType.STATE
    assert [preset.preset_id for preset in loaded.presets] == ["listening_blue"]
    assert loaded.presets[0].serialize()["params"] == {"color": "#224466"}
    assert inspected["presets"] == ["listening_blue"]
    assert verified.preset_ids == ("app.voice::listening_blue",)


def test_v2_rejects_embedded_commands(tmp_path):
    source = tmp_path / "source"
    write_effect_source(
        source,
        package_id="voice.listening",
        source_id="app.voice",
        class_name="ListeningEffect",
        effect_id="listening",
        commands={"legacy": {"kind": "state_toggle"}},
    )

    with pytest.raises(ValueError, match="does not support embedded commands"):
        validate_effect_source(source)


def test_v2_rejects_generic_common_modules_and_controller_imports(tmp_path):
    source = tmp_path / "source"
    write_effect_source(
        source,
        package_id="voice.listening",
        source_id="app.voice",
        class_name="ListeningEffect",
        effect_id="listening",
    )
    (source / "common.py").write_text("VALUE = 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="common.py"):
        validate_effect_source(source)

    (source / "common.py").unlink()
    effect_source = source / "effect.py"
    effect_source.write_text(
        "from respeaker_led.engine.runtime import ControllerRuntime\n"
        + effect_source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported module '(src|respeaker_led).engine.runtime'"):
        validate_effect_source(source)


def test_init_and_validate_v2_scaffolds(tmp_path):
    state_source = tmp_path / "state"
    overlay_source = tmp_path / "overlay"
    state = init_effect_source(
        state_source,
        effect_id="idle_blue",
        source_id="app.voice",
        definition_type="state",
    )
    overlay = init_effect_source(
        overlay_source,
        effect_id="volume",
        source_id="app.voice",
        definition_type="overlay",
        overlay_mode="controlled",
    )

    state_validation = validate_effect_source(state_source)
    overlay_validation = validate_effect_source(overlay_source)

    assert state.kind == "effect_source"
    assert overlay.kind == "effect_source"
    assert not (state_source / "commands.json").exists()
    assert state_validation.details["preset_count"] == 1
    assert overlay_validation.details["preset_count"] == 1
    assert load_effect_package(
        build_effect_package(overlay_source, tmp_path / "overlay.lefx").output_path
    ).manifest.overlay_mode is OverlayMode.CONTROLLED


def test_init_effect_batch_uses_explicit_types(tmp_path):
    batch = tmp_path / "batch.json"
    batch.write_text(
        json.dumps(
            {
                "source_id": "app.voice",
                "effects": [
                    {"effect_id": "idle", "definition_type": "state"},
                    {"effect_id": "ping", "definition_type": "event"},
                    {
                        "effect_id": "volume",
                        "definition_type": "overlay",
                        "overlay_mode": "controlled",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    results = init_effect_batch(batch, tmp_path / "generated")

    assert [result.target_path.name for result in results] == ["idle", "ping", "volume"]
    assert all(not (result.target_path / "commands.json").exists() for result in results)


def test_init_effect_batch_rejects_legacy_layer_field(tmp_path):
    batch = tmp_path / "batch.json"
    batch.write_text(
        json.dumps(
            {
                "source_id": "app.voice",
                "effects": [{"effect_id": "idle", "layer": "STATE_LAYER"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown keys: layer"):
        init_effect_batch(batch, tmp_path / "generated")


def test_build_effect_set_aggregates_unique_definitions_and_presets(tmp_path):
    source = tmp_path / "set"
    write_effect_set_source(
        source,
        source_id="app.voice",
        set_id="voice",
        title="Voice",
        effects=[
            {
                "dir_name": "idle",
                "package_id": "voice.idle",
                "class_name": "IdleEffect",
                "effect_id": "idle",
                "layer_name": "STATE_LAYER",
                "presets": {"idle_blue": {"params": {"color": "#112233"}}},
            },
            {
                "dir_name": "ping",
                "package_id": "voice.ping",
                "class_name": "PingEffect",
                "effect_id": "ping",
                "layer_name": "EVENT_LAYER",
                "presets": {"ping_red": {"params": {"color": "#FF0000"}}},
            },
        ],
    )

    output = tmp_path / "voice.lefxset"
    validation = validate_effect_set_source(source)
    build_effect_set(source, output)
    loaded = load_effect_set(output)

    assert validation.details == {"effect_count": 2, "preset_count": 2}
    assert len(validation.warnings) == 2
    assert loaded.manifest.format == "lefxset/2"
    assert [effect.manifest.effect_id for effect in loaded.effects] == ["idle", "ping"]
    assert [preset.preset_id for preset in loaded.presets] == ["idle_blue", "ping_red"]


def test_build_effect_set_from_prebuilt_packages_has_no_transition_warning(tmp_path):
    source = tmp_path / "state"
    write_effect_source(
        source,
        package_id="voice.idle",
        source_id="app.voice",
        class_name="IdleEffect",
        effect_id="idle",
    )
    package = build_effect_package(source, tmp_path / "idle.lefx").output_path
    set_source = tmp_path / "set"
    init_effect_set_source(set_source, set_id="voice", source_id="app.voice")
    (set_source / "effects" / "idle.lefx").write_bytes(package.read_bytes())
    (set_source / "set.yaml").write_text(
        "\n".join(
            [
                "set_id: voice",
                "source_id: app.voice",
                "title: Voice",
                "version: 1",
                "min_service_version: 1.0.0",
                "effects:",
                "  - idle.lefx",
            ]
        ),
        encoding="utf-8",
    )

    validation = validate_effect_set_source(set_source)

    assert validation.warnings == ()


def test_build_effect_set_rejects_mismatched_source(tmp_path):
    source = tmp_path / "foreign"
    write_effect_source(
        source,
        package_id="foreign.idle",
        source_id="app.foreign",
        class_name="ForeignEffect",
        effect_id="foreign",
    )
    package = build_effect_package(source, tmp_path / "foreign.lefx").output_path
    set_source = tmp_path / "set"
    init_effect_set_source(set_source, set_id="voice", source_id="app.voice")
    (set_source / "effects" / "foreign.lefx").write_bytes(package.read_bytes())

    with pytest.raises(ValueError, match="expected 'app.voice'"):
        build_effect_set(set_source, tmp_path / "voice.lefxset")


def test_v2_rejects_preset_lifecycle_fields(tmp_path):
    source = tmp_path / "source"
    write_effect_source(
        source,
        package_id="voice.idle",
        source_id="app.voice",
        class_name="IdleEffect",
        effect_id="idle",
        presets={
            "idle_blue": {
                "params": {"color": "#112233"},
                "target_layer": "STATE_LAYER",
            }
        },
    )

    with pytest.raises(ValueError, match="unknown keys: target_layer"):
        validate_effect_source(source)


def test_effect_set_can_be_loaded_concurrently_without_cache_collisions(tmp_path):
    source = tmp_path / "state"
    write_effect_source(
        source,
        package_id="voice.idle",
        source_id="app.voice",
        class_name="IdleEffect",
        effect_id="idle",
    )
    package = build_effect_package(source, tmp_path / "idle.lefx").output_path
    set_source = tmp_path / "set"
    init_effect_set_source(set_source, set_id="voice", source_id="app.voice")
    (set_source / "effects" / "idle.lefx").write_bytes(package.read_bytes())
    effect_set = build_effect_set(set_source, tmp_path / "voice.lefxset").output_path

    with ThreadPoolExecutor(max_workers=4) as executor:
        loaded_sets = list(executor.map(load_effect_set, [effect_set] * 8))

    assert [loaded.effects[0].manifest.effect_id for loaded in loaded_sets] == ["idle"] * 8
