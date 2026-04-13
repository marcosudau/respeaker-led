from __future__ import annotations

import json

import pytest

import tools.assemble_release_bundle as assemble_release_bundle_module
from tools.assemble_release_bundle import assemble_release_bundle
from tools.verify_release_bundle import verify_release_bundle


def test_assemble_release_bundle_copies_effect_artifacts(tmp_path, monkeypatch):
    template_root = tmp_path / "release_template"
    (template_root / "docs").mkdir(parents=True)
    (template_root / "examples").mkdir(parents=True)
    (template_root / "README.md").write_text("release template", encoding="utf-8")
    (template_root / "docs" / "HOST_APP_INTEGRATION.md").write_text("host app", encoding="utf-8")
    (template_root / "docs" / "REFERENCE.md").write_text("reference", encoding="utf-8")
    (template_root / "examples" / "led_controller_host.py").write_text("print('host')", encoding="utf-8")
    (template_root / "examples" / "example_usage.py").write_text("print('example')", encoding="utf-8")

    effects_root = tmp_path / "source_effects"
    effects_root.mkdir()
    (effects_root / "default-effects.lefxset").write_text("default", encoding="utf-8")
    (effects_root / "ignored.py").write_text("pass", encoding="utf-8")

    packages_root = tmp_path / "source_packages"
    packages_root.mkdir()
    (packages_root / "custom.lefx").write_text("custom", encoding="utf-8")

    exe_path = tmp_path / "dist" / "led_controller_service.exe"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("binary", encoding="utf-8")

    monkeypatch.setattr(assemble_release_bundle_module, "RELEASE_TEMPLATE_ROOT", template_root)
    monkeypatch.setattr(assemble_release_bundle_module, "SOURCE_EFFECTS_ROOT", effects_root)
    monkeypatch.setattr(assemble_release_bundle_module, "SOURCE_PACKAGES_ROOT", packages_root)

    bundle_root = assemble_release_bundle(version="1.2.3", exe_path=exe_path, output_dir=tmp_path / "artifacts")

    assert (bundle_root / "led_controller_service.exe").is_file()
    assert (bundle_root / "effects" / "default-effects.lefxset").read_text(encoding="utf-8") == "default"
    assert not (bundle_root / "effects" / "ignored.py").exists()
    assert (bundle_root / "packages" / "custom.lefx").read_text(encoding="utf-8") == "custom"

    manifest = json.loads((bundle_root / "bundle_manifest.json").read_text(encoding="utf-8"))
    assert manifest["effect_artifacts"] == ["effects/default-effects.lefxset", "packages/custom.lefx"]


def test_assemble_release_bundle_requires_default_effect_set(tmp_path, monkeypatch):
    template_root = tmp_path / "release_template"
    template_root.mkdir()
    (template_root / "README.md").write_text("release template", encoding="utf-8")
    exe_path = tmp_path / "dist" / "led_controller_service.exe"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("binary", encoding="utf-8")

    monkeypatch.setattr(assemble_release_bundle_module, "RELEASE_TEMPLATE_ROOT", template_root)
    monkeypatch.setattr(assemble_release_bundle_module, "SOURCE_EFFECTS_ROOT", tmp_path / "source_effects")
    monkeypatch.setattr(assemble_release_bundle_module, "SOURCE_PACKAGES_ROOT", tmp_path / "source_packages")

    with pytest.raises(FileNotFoundError, match="default-effects.lefxset"):
        assemble_release_bundle(version="1.2.3", exe_path=exe_path, output_dir=tmp_path / "artifacts")


def test_verify_release_bundle_checks_required_files(tmp_path):
    bundle_root = tmp_path / "bundle"
    (bundle_root / "docs").mkdir(parents=True)
    (bundle_root / "examples").mkdir(parents=True)
    (bundle_root / "effects").mkdir(parents=True)
    (bundle_root / "led_controller_service.exe").write_text("binary", encoding="utf-8")
    (bundle_root / "effects" / "default-effects.lefxset").write_text("default", encoding="utf-8")
    (bundle_root / "docs" / "HOST_APP_INTEGRATION.md").write_text("host app", encoding="utf-8")
    (bundle_root / "docs" / "REFERENCE.md").write_text("reference", encoding="utf-8")
    (bundle_root / "examples" / "led_controller_host.py").write_text("print('host')", encoding="utf-8")
    (bundle_root / "examples" / "example_usage.py").write_text("print('example')", encoding="utf-8")
    (bundle_root / "README.md").write_text("bundle readme", encoding="utf-8")

    result = verify_release_bundle(bundle_root)

    assert result["ok"] is True
    assert result["effect_artifacts"] == ["effects/default-effects.lefxset"]


def test_verify_release_bundle_reports_missing_required_files(tmp_path):
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with pytest.raises(FileNotFoundError, match="led_controller_service.exe"):
        verify_release_bundle(bundle_root)