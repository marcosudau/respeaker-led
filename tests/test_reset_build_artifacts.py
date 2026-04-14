from __future__ import annotations

from pathlib import Path

from tools.reset_build_artifacts import collect_cleanup_targets, reset_build_artifacts


def test_collect_cleanup_targets_only_returns_whitelisted_build_outputs(tmp_path):
    _write(tmp_path / "build" / "temp.bin", "build")
    _write(tmp_path / "dist" / "led_controller_service.exe", "exe")
    _write(tmp_path / "artifacts" / "bundle" / "bundle_manifest.json", "{}")
    _write(tmp_path / "logs" / "led_controller.log", "log")
    _write(tmp_path / ".pytest_tmp" / "state", "tmp")
    _write(tmp_path / "tools" / "effect_building" / "build_lefx" / "default-effects" / "off.lefx", "lefx")
    _write(tmp_path / "tools" / "effect_building" / "build_lefx2" / "default-effects" / "off.lefx", "lefx2")
    _write(tmp_path / "tools" / "effect_building" / "build_lefxset" / "default-effects.lefxset", "lefxset")
    _write(tmp_path / "tools" / "effect_building" / "build_lefxset2" / "default-effects.lefxset", "lefxset2")
    _write(tmp_path / "tools" / "effect_building" / "sources" / "default-effects" / "effect.yaml", "source")
    _write(tmp_path / "tools" / "effect_building" / "_generated" / "default-effects_set" / "set.yaml", "set")
    _write(tmp_path / "src" / "led_effects" / "default-effects.lefxset", "publish")
    _write(tmp_path / "src" / "led_effects" / "effects" / "default-effects.lefxset", "devcopy")
    _write(tmp_path / "release" / "led_controller_service_release_1.zip", "zip")
    _write(tmp_path / "release" / "led_controller_service_release_1" / "led_controller_service.exe", "exe")
    _write(
        tmp_path / "release" / "led_controller_service_release_1" / "runtime_state" / "effect_package_cache" / "x" / "package.lefx",
        "cache",
    )
    _write(tmp_path / "release" / "led_controller_service_release_1" / "logs" / "led_controller.log", "log")
    _write(tmp_path / "release" / "led_controller_service_release_1" / "effects" / "default-effects.lefxset", "effect-set")
    _write(tmp_path / "release" / "led_controller_service_release_1" / "packages" / "custom.lefx", "pkg")
    _write(tmp_path / "README.md", "keep")
    _write(tmp_path / "tools" / "effect_building" / "build_lefx.py", "# keep")
    _write(tmp_path / "release" / "led_controller_service_release_1" / "docs" / "REFERENCE.md", "keep")

    targets = collect_cleanup_targets(tmp_path)
    relative_paths = [target.path.relative_to(tmp_path).as_posix() for target in targets]

    assert set(relative_paths) == {
        ".pytest_tmp",
        "artifacts",
        "build",
        "dist",
        "logs",
        "release/led_controller_service_release_1/effects",
        "release/led_controller_service_release_1/led_controller_service.exe",
        "release/led_controller_service_release_1/logs",
        "release/led_controller_service_release_1/packages",
        "release/led_controller_service_release_1/runtime_state",
        "release/led_controller_service_release_1.zip",
        "src/led_effects/default-effects.lefxset",
        "src/led_effects/effects/default-effects.lefxset",
        "tools/effect_building/_generated/default-effects_set",
        "tools/effect_building/build_lefx",
        "tools/effect_building/build_lefx2",
        "tools/effect_building/build_lefxset",
        "tools/effect_building/build_lefxset2",
        "tools/effect_building/sources/default-effects",
    }
    assert "tools/effect_building/build_lefx.py" not in relative_paths
    assert "release/led_controller_service_release_1/docs/REFERENCE.md" not in relative_paths


def test_reset_build_artifacts_apply_removes_outputs_and_preserves_source_files(tmp_path):
    _write(tmp_path / "build" / "temp.bin", "build")
    _write(tmp_path / "dist" / "led_controller_service.exe", "exe")
    _write(tmp_path / "artifacts" / "bundle" / "bundle_manifest.json", "{}")
    _write(tmp_path / "logs" / "led_controller.log", "log")
    _write(tmp_path / ".pytest_tmp" / "state", "tmp")
    _write(tmp_path / "tools" / "effect_building" / "build_lefx" / "default-effects" / "off.lefx", "lefx")
    _write(tmp_path / "tools" / "effect_building" / "build_lefx.py", "# keep")
    _write(tmp_path / "tools" / "effect_building" / "sources" / "default-effects" / "effect.yaml", "source")
    _write(tmp_path / "tools" / "effect_building" / "_generated" / "default-effects_set" / "set.yaml", "set")
    _write(tmp_path / "src" / "led_effects" / "default-effects.lefxset", "publish")
    _write(tmp_path / "src" / "led_effects" / "effects" / "default-effects.lefxset", "devcopy")
    _write(tmp_path / "release" / "led_controller_service_release_1.zip", "zip")
    _write(tmp_path / "release" / "led_controller_service_release_1" / "led_controller_service.exe", "exe")
    _write(tmp_path / "release" / "led_controller_service_release_1" / "runtime_state" / "background_state.json", "{}")
    _write(tmp_path / "release" / "led_controller_service_release_1" / "logs" / "led_controller.log", "log")
    _write(tmp_path / "release" / "led_controller_service_release_1" / "effects" / "default-effects.lefxset", "effect-set")
    _write(tmp_path / "release" / "led_controller_service_release_1" / "packages" / "custom.lefx", "pkg")
    _write(tmp_path / "release" / "led_controller_service_release_1" / "docs" / "REFERENCE.md", "keep")
    _write(tmp_path / "README.md", "keep")

    preview = reset_build_artifacts(project_root=tmp_path, apply=False)
    assert preview["mode"] == "dry-run"
    assert (tmp_path / "build").exists()
    assert (tmp_path / "release" / "led_controller_service_release_1" / "docs" / "REFERENCE.md").is_file()

    result = reset_build_artifacts(project_root=tmp_path, apply=True)

    assert result["mode"] == "apply"
    assert result["target_count"] == len(result["removed"])

    assert not (tmp_path / "build").exists()
    assert not (tmp_path / "dist").exists()
    assert not (tmp_path / "artifacts").exists()
    assert not (tmp_path / "logs").exists()
    assert not (tmp_path / ".pytest_tmp").exists()
    assert not (tmp_path / "tools" / "effect_building" / "build_lefx").exists()
    assert not (tmp_path / "tools" / "effect_building" / "sources" / "default-effects").exists()
    assert not (tmp_path / "tools" / "effect_building" / "_generated" / "default-effects_set").exists()
    assert not (tmp_path / "src" / "led_effects" / "default-effects.lefxset").exists()
    assert not (tmp_path / "src" / "led_effects" / "effects" / "default-effects.lefxset").exists()
    assert not (tmp_path / "release" / "led_controller_service_release_1.zip").exists()
    assert not (tmp_path / "release" / "led_controller_service_release_1" / "led_controller_service.exe").exists()
    assert not (tmp_path / "release" / "led_controller_service_release_1" / "runtime_state").exists()
    assert not (tmp_path / "release" / "led_controller_service_release_1" / "logs").exists()
    assert not (tmp_path / "release" / "led_controller_service_release_1" / "effects").exists()
    assert not (tmp_path / "release" / "led_controller_service_release_1" / "packages").exists()

    assert (tmp_path / "README.md").is_file()
    assert (tmp_path / "tools" / "effect_building" / "build_lefx.py").is_file()
    assert (tmp_path / "release" / "led_controller_service_release_1" / "docs" / "REFERENCE.md").is_file()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
