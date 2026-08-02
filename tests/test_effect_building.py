from __future__ import annotations

import json
from pathlib import Path

from src.engine.effect_package_loader import load_effect_package, load_effect_set
from tools.effect_building.build_lefx import main as build_lefx_main
from tools.effect_building.build_lefxset import main as build_lefxset_main
from tools.effect_building.standard_effects import cleanup_standard_build_cache, discover_standard_effects


def test_standard_effect_build_scripts_generate_self_contained_packages_and_default_set(tmp_path, capsys):
    sources_root = tmp_path / "sources"
    lefx_root = tmp_path / "build_lefx"
    lefxset_root = tmp_path / "build_lefxset"
    publish_copy = tmp_path / "published" / "default-effects.lefxset"

    assert build_lefx_main(["--sources-root", str(sources_root), "--output-root", str(lefx_root)]) == 0
    build_payload = json.loads(capsys.readouterr().out)

    expected_effects = discover_standard_effects()
    assert build_payload["effect_count"] == len(expected_effects)
    package_paths = [Path(item) for item in build_payload["packages"]]
    assert len(package_paths) == len(expected_effects)

    definition_types = set()
    for package_path in package_paths:
        loaded = load_effect_package(package_path)
        assert len(loaded.presets) >= 4
        definition_types.add(loaded.manifest.definition_type.value)
        assert all(set(preset.serialize()) >= {"params", "preset_id"} for preset in loaded.presets)

    assert definition_types == {"state", "overlay", "event"}

    assert build_lefxset_main(
        [
            "--packages-root",
            str(lefx_root),
            "--output-root",
            str(lefxset_root),
            "--publish-copy",
            str(publish_copy),
        ]
    ) == 0
    set_payload = json.loads(capsys.readouterr().out)

    effect_set_path = Path(set_payload["effect_set"])
    assert set_payload["cache_cleaned"] is False
    assert effect_set_path.exists()
    assert publish_copy.exists()

    loaded_set = load_effect_set(effect_set_path)
    assert len(loaded_set.effects) == len(expected_effects)
    assert len(loaded_set.presets) >= len(expected_effects) * 4
    assert {effect.manifest.effect_id for effect in loaded_set.effects} == {spec.effect_id for spec in expected_effects}


def test_standard_effect_cache_cleanup_preserves_finished_outputs(tmp_path):
    cache_root = tmp_path / "build" / ".cache"
    output_path = tmp_path / "build" / "output" / "default-effects.lefxset"
    (cache_root / "sources").mkdir(parents=True)
    (cache_root / "sources" / "effect.py").write_text("generated", encoding="utf-8")
    output_path.parent.mkdir(parents=True)
    output_path.write_text("finished", encoding="utf-8")

    cleanup_standard_build_cache(cache_root)

    assert not cache_root.exists()
    assert output_path.read_text(encoding="utf-8") == "finished"
