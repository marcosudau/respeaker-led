from __future__ import annotations

import importlib.util
import json
import runpy
import tomllib
from pathlib import Path

import pytest

from tests.build_artifact_helpers import load_build_tool_module


create_release_bundle_module = load_build_tool_module("create_release_bundle")
check_release_bundle_module = load_build_tool_module("check_release_bundle")
create_release_bundle = create_release_bundle_module.create_release_bundle
verify_release_bundle = check_release_bundle_module.verify_release_bundle


def test_create_release_bundle_copies_effect_artifacts_into_zip(tmp_path):
    template_root = tmp_path / "template_release_bundle"
    (template_root / "docs").mkdir(parents=True)
    (template_root / "examples").mkdir(parents=True)
    (template_root / "README.md").write_text("release template", encoding="utf-8")
    (template_root / "docs" / "HOST_APP_INTEGRATION.md").write_text("host app", encoding="utf-8")
    (template_root / "docs" / "REFERENCE.md").write_text("reference", encoding="utf-8")
    (template_root / "examples" / "led_controller_host.py").write_text("print('host')", encoding="utf-8")
    (template_root / "examples" / "example_usage.py").write_text("print('example')", encoding="utf-8")

    effects_root = tmp_path / "built_effects"
    effects_root.mkdir()
    (effects_root / "default-effects.lefxset").write_text("default", encoding="utf-8")

    packages_root = tmp_path / "built_packages"
    (packages_root / "nested").mkdir(parents=True)
    (packages_root / "nested" / "custom.lefx").write_text("custom", encoding="utf-8")

    config_path = tmp_path / "build_config.json"
    config_path.write_text(
        json.dumps(
            {
                "builtin-effects-discovery": [
                    str(effects_root / "default-effects.lefxset"),
                    str(packages_root),
                ]
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    exe_path = tmp_path / "dist" / "led_controller_service_1.2.3.exe"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("binary", encoding="utf-8")

    manifest = create_release_bundle(
        exe_path=exe_path,
        output_dir=tmp_path / "dist" / "release_bundle",
        template_root=template_root,
        config_path=config_path,
        version="1.2.3",
        include_version=True,
        force=False,
    )

    archive_path = Path(str(manifest["archive_path"]))
    assert archive_path.is_file()
    assert not (archive_path.parent / "_staging").exists()

    verification = verify_release_bundle(archive_path)
    assert verification["ok"] is True
    assert verification["exe_name"] == "led_controller_service_1.2.3.exe"
    assert verification["effect_artifacts"] == ["effects/default-effects.lefxset", "packages/nested/custom.lefx"]


def test_create_release_bundle_requires_default_effect_set(tmp_path):
    template_root = tmp_path / "template_release_bundle"
    template_root.mkdir()
    (template_root / "README.md").write_text("release template", encoding="utf-8")
    config_path = tmp_path / "build_config.json"
    config_path.write_text(json.dumps({"builtin-effects-discovery": []}, ensure_ascii=True, indent=2), encoding="utf-8")
    exe_path = tmp_path / "dist" / "led_controller_service.exe"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("binary", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="default-effects.lefxset"):
        create_release_bundle(
            exe_path=exe_path,
            output_dir=tmp_path / "dist" / "release_bundle",
            template_root=template_root,
            config_path=config_path,
            version="1.2.3",
            include_version=False,
            force=False,
        )


def test_verify_release_bundle_reports_missing_required_files(tmp_path):
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with pytest.raises(FileNotFoundError, match="\\*\\.exe"):
        verify_release_bundle(bundle_root)


def test_spec_uses_local_build_hooks():
    spec_path = Path("build-tools/led_controller_service.spec")
    assert "hookspath=[str(BUILD_TOOLS_ROOT / \"hooks\")]" in spec_path.read_text(encoding="utf-8")


def test_custom_importlib_resources_hook_skips_missing_trees_module():
    hook_path = Path("build-tools/hooks/hook-importlib_resources.py")
    namespace = runpy.run_path(str(hook_path))
    expected = ["importlib_resources.trees"] if importlib.util.find_spec("importlib_resources.trees") else []
    assert namespace["hiddenimports"] == expected


def test_pyproject_declares_tzdata_for_windows_builds():
    payload = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = payload["project"]["dependencies"]
    assert any(
        isinstance(entry, str) and entry.startswith("tzdata>=") and "platform_system == 'Windows'" in entry
        for entry in dependencies
    )
