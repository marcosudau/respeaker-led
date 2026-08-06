from __future__ import annotations

from pathlib import Path

from tests.build_artifact_helpers import default_effect_set_path
from tools.effect_building.effect_set_sources import (
    DEFAULT_BUILD_ROOT,
    DEFAULT_SOURCES_ROOT,
    discover_effect_sets,
    discover_effect_sources,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src" / "respeaker_led"


def test_core_source_has_no_legacy_widget_or_quick_action_imports():
    legacy_markers = [
        "widget_loader",
        "quick_actions_layer",
        "list-widgets",
        "/api/v1/widgets",
        "/api/v1/quick-actions",
        "/api/v1/work",
        "/api/v1/state-layer/visual",
        "/api/v1/main-layer/visual",
        "/api/v1/event-layer",
        "serve-api",
        "push-event",
        "showcase_app",
        "standard_effect_library",
        "MAIN_LAYER",
        "effect_command_registry",
        "respeaker_led.engine.normalization",
        "/api/v1/commands/apply_effect",
        "/api/v1/commands/clear_layer",
    ]

    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for marker in legacy_markers:
            assert marker not in text, f"Found legacy marker {marker!r} in {path}"


def test_builtin_effects_are_configured_outside_src():
    assert (PROJECT_ROOT / "build-tools" / "build_config.json").is_file()
    assert default_effect_set_path().is_file()
    assert not (SRC_ROOT / "led_effects" / "effects" / "default-effects.lefxset").exists()
    assert not (SRC_ROOT / "builtin_effects.py").exists()


def test_standard_effect_sources_are_typed_autonomous_and_outside_build_output():
    sources_root = DEFAULT_SOURCES_ROOT.resolve()
    build_root = DEFAULT_BUILD_ROOT.resolve()

    assert not sources_root.is_relative_to(build_root)
    assert not (PROJECT_ROOT / "tools" / "effect_building" / "effect_definitions").exists()
    assert not (PROJECT_ROOT / "tools" / "effect_building" / "sorted_by_type").exists()
    assert not (sources_root / "states").exists()
    assert not (sources_root / "overlays").exists()
    assert not (sources_root / "events").exists()
    assert (sources_root / "default-effects" / "set.yaml").is_file()
    assert (sources_root / "smartspeaker-set" / "set.yaml").is_file()

    effect_sets = discover_effect_sets()
    assert [effect_set.set_id for effect_set in effect_sets] == ["default-effects", "smartspeaker-set"]
    default_set = next(effect_set for effect_set in effect_sets if effect_set.set_id == "default-effects")
    specs = discover_effect_sources(default_set)
    assert len(specs) == 34
    for spec in specs:
        definition = spec.effect_class.get_definition()
        assert spec.source_dir.name == definition.id
        assert spec.source_dir.parent.name == f"{definition.definition_type.value}s"
        assert (spec.source_dir / "effect.py").is_file()
        assert (spec.source_dir / "effect.yaml").is_file()
        assert (spec.source_dir / "presets.yaml").is_file()
        assert not list(spec.source_dir.rglob("common.py"))

        source_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in spec.source_dir.rglob("*.py")
        )
        assert "effect_definitions" not in source_text
        assert "sorted_by_type" not in source_text
