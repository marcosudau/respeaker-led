from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from respeaker_led.engine.effect_package_builder import build_effect_package, build_effect_set, validate_effect_set_source
from respeaker_led.engine.effect_package_loader import load_effect_package, load_effect_set
from tests.package_test_utils import write_effect_source
from tools.effect_building.build_lefx import main as build_lefx_main
from tools.effect_building.build_lefxset import main as build_lefxset_main
from tools.effect_building.effect_set_builder import (
    build_all_effect_packages,
    build_all_effect_sets,
    build_effect_set_for_source,
    cleanup_effect_build_cache,
)
from tools.effect_building.effect_set_sources import (
    DEFAULT_BUILD_CACHE_ROOT,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_PACKAGE_CACHE_ROOT,
    DEFAULT_PUBLISH_ROOT,
    DEFAULT_SOURCES_ROOT,
    EffectSetSource,
    discover_effect_sets,
    discover_effect_sources,
)


def _write_set_manifest(
    set_dir: Path,
    *,
    set_id: str,
    source_id: str,
    title: str = "Test Set",
    extra_keys: dict | None = None,
) -> None:
    lines = [
        f"set_id: {set_id}",
        f"source_id: {source_id}",
        f"title: {title}",
        "version: 1",
        "min_service_version: 1.0.0",
        "tags:",
        "  - test",
    ]
    for key, value in (extra_keys or {}).items():
        lines.append(f"{key}: {value}")
    set_dir.mkdir(parents=True, exist_ok=True)
    (set_dir / "set.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_minimal_source(
    sources_root: Path,
    *,
    set_id: str,
    effect_id: str = "idle",
    source_id: str | None = None,
    layer_name: str = "STATE_LAYER",
    package_id: str | None = None,
) -> None:
    source_id = source_id or set_id
    set_dir = sources_root / set_id
    _write_set_manifest(set_dir, set_id=set_id, source_id=source_id)
    type_dir = "states" if layer_name == "STATE_LAYER" else ("events" if layer_name == "EVENT_LAYER" else "overlays")
    write_effect_source(
        set_dir / type_dir / effect_id,
        package_id=package_id or f"{source_id}.{effect_id}",
        source_id=source_id,
        class_name="IdleEffect",
        effect_id=effect_id,
        layer_name=layer_name,
    )


def _default_effect_set() -> EffectSetSource:
    for effect_set in discover_effect_sets():
        if effect_set.set_id == "default-effects":
            return effect_set
    raise AssertionError("default-effects set not discovered")


# ---------------------------------------------------------------------------
# 13.1 Discovery
# ---------------------------------------------------------------------------


def test_discovery_finds_both_real_sets_deterministically():
    sets = discover_effect_sets()

    assert [effect_set.set_id for effect_set in sets] == ["default-effects", "smartspeaker-set"]
    assert [effect_set.source_id for effect_set in sets] == ["default-effects", "smartspeaker-set"]
    assert [effect_set.version for effect_set in sets] == [1, 1]


def test_discovery_counts_match_expected_sources():
    default_sources = discover_effect_sources(_default_effect_set())
    smartspeaker_set = next(effect_set for effect_set in discover_effect_sets() if effect_set.set_id == "smartspeaker-set")
    smartspeaker_sources = discover_effect_sources(smartspeaker_set)

    assert len(default_sources) == 34
    assert len(smartspeaker_sources) == 23
    assert len(default_sources) + len(smartspeaker_sources) == 57

    default_ids = {spec.effect_id for spec in default_sources}
    smartspeaker_ids = {spec.effect_id for spec in smartspeaker_sources}
    assert len(default_ids) == 34
    assert len(smartspeaker_ids) == 23
    for spec in default_sources:
        assert spec.source_id == "default-effects"
        assert spec.package_id == f"default-effects.{spec.effect_id}"
        assert spec.source_dir.parent.parent.name == "default-effects"
    for spec in smartspeaker_sources:
        assert spec.source_id == "smartspeaker-set"
        assert spec.package_id == f"smartspeaker-set.{spec.effect_id}"


def test_discovery_rejects_duplicate_set_id(tmp_path):
    sources_root = tmp_path / "sources"
    _write_minimal_source(sources_root, set_id="alpha")
    _write_set_manifest(sources_root / "beta", set_id="alpha", source_id="beta-source")

    with pytest.raises(ValueError, match="Duplicate set_id"):
        discover_effect_sets(sources_root)


def test_discovery_rejects_duplicate_source_id(tmp_path):
    sources_root = tmp_path / "sources"
    _write_minimal_source(sources_root, set_id="alpha", source_id="shared")
    _write_minimal_source(sources_root, set_id="beta", source_id="shared")

    with pytest.raises(ValueError, match="Duplicate source_id"):
        discover_effect_sets(sources_root)


def test_discovery_rejects_folder_name_mismatch(tmp_path):
    sources_root = tmp_path / "sources"
    _write_set_manifest(sources_root / "wrong-name", set_id="right-name", source_id="right-name")

    with pytest.raises(ValueError, match="must match set_id"):
        discover_effect_sets(sources_root)


def test_discovery_rejects_orphaned_legacy_source(tmp_path):
    sources_root = tmp_path / "sources"
    _write_minimal_source(sources_root, set_id="alpha")
    write_effect_source(
        sources_root / "states" / "legacy_effect",
        package_id="alpha.legacy_effect",
        source_id="alpha",
        class_name="LegacyEffect",
        effect_id="legacy_effect",
    )

    with pytest.raises(ValueError, match="Orphaned/legacy"):
        discover_effect_sets(sources_root)


def test_discovery_fails_clearly_without_any_set(tmp_path):
    sources_root = tmp_path / "sources"
    sources_root.mkdir()

    with pytest.raises(ValueError, match="No effect sets discovered"):
        discover_effect_sets(sources_root)


def test_discovery_rejects_effect_source_in_wrong_type_folder(tmp_path):
    sources_root = tmp_path / "sources"
    set_dir = sources_root / "alpha"
    _write_set_manifest(set_dir, set_id="alpha", source_id="alpha")
    write_effect_source(
        set_dir / "events" / "idle",
        package_id="alpha.idle",
        source_id="alpha",
        class_name="IdleEffect",
        effect_id="idle",
        layer_name="STATE_LAYER",
    )
    effect_set = discover_effect_sets(sources_root)[0]

    with pytest.raises(ValueError, match="belongs under 'states'"):
        discover_effect_sources(effect_set)


def test_discovery_rejects_wrong_source_id(tmp_path):
    sources_root = tmp_path / "sources"
    set_dir = sources_root / "alpha"
    _write_set_manifest(set_dir, set_id="alpha", source_id="alpha")
    write_effect_source(
        set_dir / "states" / "idle",
        package_id="alpha.idle",
        source_id="foreign",
        class_name="IdleEffect",
        effect_id="idle",
    )
    effect_set = discover_effect_sets(sources_root)[0]

    with pytest.raises(ValueError, match="expected 'alpha'"):
        discover_effect_sources(effect_set)


def test_discovery_rejects_wrong_package_id(tmp_path):
    sources_root = tmp_path / "sources"
    set_dir = sources_root / "alpha"
    _write_set_manifest(set_dir, set_id="alpha", source_id="alpha")
    write_effect_source(
        set_dir / "states" / "idle",
        package_id="alpha.wrong",
        source_id="alpha",
        class_name="IdleEffect",
        effect_id="idle",
    )
    effect_set = discover_effect_sets(sources_root)[0]

    with pytest.raises(ValueError, match="must use package_id"):
        discover_effect_sources(effect_set)


def test_discovery_rejects_unknown_set_manifest_keys(tmp_path):
    sources_root = tmp_path / "sources"
    _write_set_manifest(
        sources_root / "alpha",
        set_id="alpha",
        source_id="alpha",
        extra_keys={"bogus": "value"},
    )

    with pytest.raises(ValueError, match="unknown keys: bogus"):
        discover_effect_sets(sources_root)


# ---------------------------------------------------------------------------
# 13.2 Package build
# ---------------------------------------------------------------------------


def test_build_lefx_builds_both_sets_into_separate_package_dirs(tmp_path, capsys):
    package_root = tmp_path / "packages"

    assert build_lefx_main(["--sources-root", str(DEFAULT_SOURCES_ROOT), "--output-root", str(package_root)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["set_count"] == 2
    assert payload["effect_count"] == 57
    assert payload["sets"]["default-effects"]["effect_count"] == 34
    assert payload["sets"]["smartspeaker-set"]["effect_count"] == 23

    default_package_dir = package_root / "default-effects"
    smartspeaker_package_dir = package_root / "smartspeaker-set"
    assert sorted(path.stem for path in default_package_dir.glob("*.lefx")) == sorted(
        payload["sets"]["default-effects"]["effect_ids"]
    )
    assert sorted(path.stem for path in smartspeaker_package_dir.glob("*.lefx")) == sorted(
        payload["sets"]["smartspeaker-set"]["effect_ids"]
    )
    assert len(list(default_package_dir.glob("*.lefx"))) == 34
    assert len(list(smartspeaker_package_dir.glob("*.lefx"))) == 23

    for package_path in [*default_package_dir.glob("*.lefx"), *smartspeaker_package_dir.glob("*.lefx")]:
        loaded = load_effect_package(package_path)
        assert loaded.manifest.format == "lefx/2"
        assert len(loaded.presets) >= 1
        assert all(set(preset.serialize()) >= {"params", "preset_id"} for preset in loaded.presets)

    for package_path in default_package_dir.glob("*.lefx"):
        loaded = load_effect_package(package_path)
        assert len(loaded.presets) >= 4


def test_build_all_effect_packages_smoke_renders_every_source(tmp_path):
    packages = build_all_effect_packages(
        sources_root=DEFAULT_SOURCES_ROOT,
        package_cache_root=tmp_path / "packages",
    )

    assert {set_id: len(paths) for set_id, paths in packages.items()} == {
        "default-effects": 34,
        "smartspeaker-set": 23,
    }
    for paths in packages.values():
        assert len(paths) == len(set(paths))


# ---------------------------------------------------------------------------
# 13.3 Set build
# ---------------------------------------------------------------------------


def test_build_lefxset_builds_both_sets_from_prebuilt_packages(tmp_path, capsys):
    package_root = tmp_path / "packages"
    output_root = tmp_path / "output"
    publish_root = tmp_path / "published"

    assert build_lefx_main(["--sources-root", str(DEFAULT_SOURCES_ROOT), "--output-root", str(package_root)]) == 0
    capsys.readouterr()

    assert build_lefxset_main(
        [
            "--sources-root",
            str(DEFAULT_SOURCES_ROOT),
            "--packages-root",
            str(package_root),
            "--output-root",
            str(output_root),
            "--publish-root",
            str(publish_root),
        ]
    ) == 0
    set_payload = json.loads(capsys.readouterr().out)

    assert set_payload["ok"] is True
    assert set_payload["set_count"] == 2
    assert set_payload["effect_count"] == 57
    assert set_payload["cache_cleaned"] is False

    default_set = output_root / "default-effects.lefxset"
    smartspeaker_set = output_root / "smartspeaker-set.lefxset"
    assert default_set.is_file()
    assert smartspeaker_set.is_file()
    assert (publish_root / "default-effects.lefxset").is_file()
    assert (publish_root / "smartspeaker-set.lefxset").is_file()

    loaded_default = load_effect_set(default_set)
    loaded_smartspeaker = load_effect_set(smartspeaker_set)
    assert len(loaded_default.effects) == 34
    assert len(loaded_smartspeaker.effects) == 23

    expected_default_ids = {spec.effect_id for spec in discover_effect_sources(_default_effect_set())}
    smartspeaker_set_source = next(
        effect_set for effect_set in discover_effect_sets() if effect_set.set_id == "smartspeaker-set"
    )
    expected_smartspeaker_ids = {spec.effect_id for spec in discover_effect_sources(smartspeaker_set_source)}

    assert {effect.manifest.effect_id for effect in loaded_default.effects} == expected_default_ids
    assert {effect.manifest.effect_id for effect in loaded_smartspeaker.effects} == expected_smartspeaker_ids
    assert len({effect.manifest.effect_id for effect in loaded_default.effects}) == 34
    assert len({effect.manifest.effect_id for effect in loaded_smartspeaker.effects}) == 23


def test_set_build_from_prebuilt_packages_has_no_transition_warning(tmp_path):
    sources_root = tmp_path / "sources"
    _write_minimal_source(sources_root, set_id="alpha", effect_id="idle")
    effect_set = discover_effect_sets(sources_root)[0]

    build_all_effect_packages(sources_root=sources_root, package_cache_root=tmp_path / "packages")
    build_effect_set_for_source(
        effect_set,
        package_cache_root=tmp_path / "packages",
        output_root=tmp_path / "output",
        publish_root=None,
        work_root=tmp_path / "work",
    )

    validation = validate_effect_set_source(tmp_path / "work" / "alpha")
    assert validation.warnings == ()


def test_set_build_rejects_missing_package(tmp_path):
    sources_root = tmp_path / "sources"
    _write_minimal_source(sources_root, set_id="alpha", effect_id="idle")
    effect_set = discover_effect_sets(sources_root)[0]

    build_all_effect_packages(sources_root=sources_root, package_cache_root=tmp_path / "packages")
    (tmp_path / "packages" / "alpha" / "idle.lefx").unlink()

    with pytest.raises(ValueError, match="missing prebuilt packages"):
        build_effect_set_for_source(
            effect_set,
            package_cache_root=tmp_path / "packages",
            output_root=tmp_path / "output",
            publish_root=None,
            work_root=tmp_path / "work",
        )


def test_set_build_rejects_stale_extra_package(tmp_path):
    sources_root = tmp_path / "sources"
    _write_minimal_source(sources_root, set_id="alpha", effect_id="idle")
    effect_set = discover_effect_sets(sources_root)[0]

    build_all_effect_packages(sources_root=sources_root, package_cache_root=tmp_path / "packages")
    stale = tmp_path / "packages" / "alpha" / "stale.lefx"
    stale.write_bytes((tmp_path / "packages" / "alpha" / "idle.lefx").read_bytes())

    with pytest.raises(ValueError, match="unexpected/stale packages"):
        build_effect_set_for_source(
            effect_set,
            package_cache_root=tmp_path / "packages",
            output_root=tmp_path / "output",
            publish_root=None,
            work_root=tmp_path / "work",
        )


def test_set_build_rejects_package_with_wrong_source_id(tmp_path):
    sources_root = tmp_path / "sources"
    _write_minimal_source(sources_root, set_id="alpha", effect_id="idle")
    effect_set = discover_effect_sets(sources_root)[0]

    build_all_effect_packages(sources_root=sources_root, package_cache_root=tmp_path / "packages")

    foreign_source = tmp_path / "foreign"
    write_effect_source(
        foreign_source,
        package_id="foreign.idle",
        source_id="foreign",
        class_name="ForeignEffect",
        effect_id="idle",
    )
    foreign_package = build_effect_package(foreign_source, tmp_path / "foreign.lefx").output_path
    (tmp_path / "packages" / "alpha" / "idle.lefx").write_bytes(foreign_package.read_bytes())

    with pytest.raises(ValueError, match="source_id"):
        build_effect_set_for_source(
            effect_set,
            package_cache_root=tmp_path / "packages",
            output_root=tmp_path / "output",
            publish_root=None,
            work_root=tmp_path / "work",
        )


def test_build_lefxset_rebuild_packages_builds_both_stages(tmp_path, capsys):
    package_root = tmp_path / "packages"
    output_root = tmp_path / "output"
    publish_root = tmp_path / "published"

    assert build_lefxset_main(
        [
            "--sources-root",
            str(DEFAULT_SOURCES_ROOT),
            "--packages-root",
            str(package_root),
            "--output-root",
            str(output_root),
            "--publish-root",
            str(publish_root),
            "--rebuild-packages",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["set_count"] == 2
    assert payload["effect_count"] == 57
    assert len(list((package_root / "default-effects").glob("*.lefx"))) == 34
    assert len(list((package_root / "smartspeaker-set").glob("*.lefx"))) == 23
    assert load_effect_set(output_root / "default-effects.lefxset")
    assert load_effect_set(output_root / "smartspeaker-set.lefxset")


def test_cache_keep_and_cleanup_for_shared_cache_structure(capsys):
    cache_root = DEFAULT_BUILD_CACHE_ROOT
    output_root = DEFAULT_OUTPUT_ROOT
    published_root = DEFAULT_PUBLISH_ROOT

    assert build_lefxset_main(["--rebuild-packages", "--keep-cache"]) == 0
    keep_payload = json.loads(capsys.readouterr().out)
    assert keep_payload["cache_cleaned"] is False
    assert cache_root.is_dir()
    assert (output_root / "default-effects.lefxset").is_file()
    assert (output_root / "smartspeaker-set.lefxset").is_file()
    assert (published_root / "default-effects.lefxset").is_file()
    assert (published_root / "smartspeaker-set.lefxset").is_file()

    assert build_lefxset_main([]) == 0
    cleanup_payload = json.loads(capsys.readouterr().out)
    assert cleanup_payload["cache_cleaned"] is True
    assert not cache_root.exists()
    assert (output_root / "default-effects.lefxset").is_file()
    assert (output_root / "smartspeaker-set.lefxset").is_file()


def test_cleanup_effect_build_cache_removes_only_cache(tmp_path):
    cache_root = tmp_path / "build" / ".cache"
    output_path = tmp_path / "build" / "output" / "default-effects.lefxset"
    (cache_root / "build_lefx").mkdir(parents=True)
    (cache_root / "build_lefx" / "effect.py").write_text("generated", encoding="utf-8")
    output_path.parent.mkdir(parents=True)
    output_path.write_text("finished", encoding="utf-8")

    cleanup_effect_build_cache(cache_root)

    assert not cache_root.exists()
    assert output_path.read_text(encoding="utf-8") == "finished"


# ---------------------------------------------------------------------------
# 13.4 Extensibility: a third set needs no production code change
# ---------------------------------------------------------------------------


def test_third_set_is_discovered_packaged_and_built_without_code_change(tmp_path, capsys):
    sources_root = tmp_path / "sources"
    _write_minimal_source(sources_root, set_id="third-set", effect_id="blink_extra")
    package_root = tmp_path / "packages"
    output_root = tmp_path / "output"
    publish_root = tmp_path / "published"

    assert [effect_set.set_id for effect_set in discover_effect_sets(sources_root)] == ["third-set"]

    assert build_lefx_main(["--sources-root", str(sources_root), "--output-root", str(package_root)]) == 0
    build_payload = json.loads(capsys.readouterr().out)
    assert build_payload["set_count"] == 1
    assert build_payload["effect_count"] == 1
    assert (package_root / "third-set" / "blink_extra.lefx").is_file()

    assert build_lefxset_main(
        [
            "--sources-root",
            str(sources_root),
            "--packages-root",
            str(package_root),
            "--output-root",
            str(output_root),
            "--publish-root",
            str(publish_root),
        ]
    ) == 0
    set_payload = json.loads(capsys.readouterr().out)
    assert set_payload["set_count"] == 1
    assert set_payload["effect_count"] == 1

    effect_set_path = output_root / "third-set.lefxset"
    assert effect_set_path.is_file()
    loaded = load_effect_set(effect_set_path)
    assert [effect.manifest.effect_id for effect in loaded.effects] == ["blink_extra"]
