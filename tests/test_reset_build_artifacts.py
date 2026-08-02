from __future__ import annotations

from pathlib import Path

from tests.build_artifact_helpers import load_build_tool_module


cleanup_after_build_module = load_build_tool_module("cleanup_after_build")
cleanup_after_build = cleanup_after_build_module.cleanup_after_build


def test_cleanup_after_build_creates_missing_config_and_preserves_deliverables(tmp_path):
    _write(tmp_path / "build" / "temp.bin", "build")
    _write(tmp_path / "dist" / "led_controller_service_1.2.3.exe", "exe")
    _write(tmp_path / "dist" / "verify_release_binary_service.log", "log")
    _write(tmp_path / "dist" / "release_bundle" / "led_controller_service_1.2.3_windows_x64.zip", "zip")
    _write(tmp_path / "dist" / "release_bundle" / "_staging" / "bundle" / "bundle_manifest.json", "{}")
    _write(tmp_path / "logs" / "led_controller.log", "log")
    _write(tmp_path / ".pytest_tmp" / "state", "tmp")
    _write(tmp_path / ".pytest_tmp_full" / "state", "tmp")
    _write(tmp_path / "tests" / ".cache" / "pytest_cache" / "state", "tmp")
    _write(tmp_path / "docs" / "examples" / "effects" / ".cache" / "tutorial.lefx", "tmp")
    _write(tmp_path / "tools" / "effect_building" / "build" / ".cache" / "sources" / "effect.py", "tmp")
    _write(tmp_path / "src" / "__pycache__" / "module.pyc", "tmp")
    _write(tmp_path / "tools" / "effect_building" / "build" / "output" / "default-effects.lefxset", "finished")

    config_path = tmp_path / "build-tools" / "scripts" / "cleanup_paths.json"
    result = cleanup_after_build(config_path=config_path, complete=False, dry_run=False, project_root=tmp_path)

    assert result["created_config"] is True
    assert result["mode"] == "default"
    assert not (tmp_path / "build").exists()
    assert not (tmp_path / "logs").exists()
    assert not (tmp_path / ".pytest_tmp").exists()
    assert not (tmp_path / ".pytest_tmp_full").exists()
    assert not (tmp_path / "tests" / ".cache").exists()
    assert not (tmp_path / "docs" / "examples" / "effects" / ".cache").exists()
    assert not (tmp_path / "tools" / "effect_building" / "build" / ".cache").exists()
    assert not (tmp_path / "src" / "__pycache__").exists()
    assert (tmp_path / "tools" / "effect_building" / "build" / "output" / "default-effects.lefxset").is_file()
    assert not (tmp_path / "dist" / "release_bundle" / "_staging").exists()
    assert (tmp_path / "dist" / "led_controller_service_1.2.3.exe").is_file()
    assert (tmp_path / "dist" / "release_bundle" / "led_controller_service_1.2.3_windows_x64.zip").is_file()


def test_cleanup_after_build_complete_also_removes_exe_and_bundle(tmp_path):
    _write(tmp_path / "dist" / "led_controller_service_1.2.3.exe", "exe")
    _write(tmp_path / "dist" / "release_bundle" / "led_controller_service_1.2.3_windows_x64.zip", "zip")
    config_path = tmp_path / "build-tools" / "scripts" / "cleanup_paths.json"

    cleanup_after_build(config_path=config_path, complete=False, dry_run=False, project_root=tmp_path)
    result = cleanup_after_build(config_path=config_path, complete=True, dry_run=False, project_root=tmp_path)

    assert result["mode"] == "complete"
    assert not (tmp_path / "dist" / "led_controller_service_1.2.3.exe").exists()
    assert not (tmp_path / "dist" / "release_bundle" / "led_controller_service_1.2.3_windows_x64.zip").exists()


def test_cleanup_after_build_dry_run_leaves_files_untouched(tmp_path):
    _write(tmp_path / "build" / "temp.bin", "build")
    config_path = tmp_path / "build-tools" / "scripts" / "cleanup_paths.json"

    result = cleanup_after_build(config_path=config_path, complete=False, dry_run=True, project_root=tmp_path)

    assert result["mode"] == "dry-run"
    assert (tmp_path / "build").exists()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
