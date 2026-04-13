from __future__ import annotations

import json
from pathlib import Path

from src.engine.effect_package_loader import load_effect_package, load_effect_set
from tools.effect_building.build_lefx import main as build_lefx_main
from tools.effect_building.build_lefxset import main as build_lefxset_main
from tools.effect_building.standard_effects import discover_standard_effects


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

    state_capable_packages = 0
    for package_path in package_paths:
        loaded = load_effect_package(package_path)
        assert len(loaded.presets) >= 4
        assert len(loaded.commands) == len(loaded.presets)
        if any(preset.category == "state" for preset in loaded.presets):
            state_capable_packages += 1
            assert sum(1 for preset in loaded.presets if preset.category == "state") >= 2

    assert state_capable_packages > 0

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
    assert effect_set_path.exists()
    assert publish_copy.exists()

    loaded_set = load_effect_set(effect_set_path)
    assert len(loaded_set.effects) == len(expected_effects)
    assert len(loaded_set.presets) >= len(expected_effects) * 4
    assert {effect.manifest.effect_id for effect in loaded_set.effects} == {spec.effect_id for spec in expected_effects}