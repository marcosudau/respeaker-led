from __future__ import annotations

import json

import pytest

from src.core.models import LED_COUNT
from src.engine.preset_loader import PresetRegistry


def write_preset_pack(folder, *, preset_id: str, command: str):
    folder.mkdir()
    (folder / "preset.yaml").write_text(
        "\n".join(
            [
                f"id: {preset_id}",
                "name: Demo Preset",
                "description: Demo preset for tests",
                f"command: {command}",
                "sample_spec: sample.json",
                "tags:",
                "  - demo",
            ]
        ),
        encoding="utf-8",
    )
    (folder / "sample.json").write_text(json.dumps({"color": "0x112233"}), encoding="utf-8")
    (folder / "preset.py").write_text(
        "\n".join(
            [
                "from src.engine.effects import solid",
                "from src.core.models import PresetBuildResult",
                "from src.infrastructure.spec_utils import parse_hex_color",
                "",
                "def build_preset(spec):",
                "    color = parse_hex_color(spec.get('color', '0x112233'))",
                "    return PresetBuildResult(",
                f"        preset_id='{preset_id}',",
                "        mode='solid',",
                "        payload={'color': color},",
                "        visual=solid(color),",
                "    )",
            ]
        ),
        encoding="utf-8",
    )


def test_discovery_returns_empty_registry_when_root_is_missing(tmp_path):
    missing = tmp_path / "does-not-exist"

    registry = PresetRegistry.discover(missing)

    assert registry.list_presets() == []


def test_discovery_finds_valid_preset_pack(tmp_path):
    write_preset_pack(tmp_path / "demo_pack", preset_id="demo", command="demo-pack")

    registry = PresetRegistry.discover(tmp_path)

    preset = registry.get_by_id("demo")
    assert preset.manifest.command == "demo-pack"
    assert preset.sample_path is not None
    assert len(registry.list_presets()) == 1


def test_invalid_manifest_fails_clearly(tmp_path):
    broken = tmp_path / "broken_pack"
    broken.mkdir()
    (broken / "preset.yaml").write_text("id: broken\nname: Broken", encoding="utf-8")
    (broken / "preset.py").write_text("def build_preset(spec):\n    return spec", encoding="utf-8")

    with pytest.raises(ValueError, match="missing keys"):
        PresetRegistry.discover(tmp_path)


def test_duplicate_ids_fail_clearly(tmp_path):
    write_preset_pack(tmp_path / "pack_one", preset_id="dup", command="one")
    write_preset_pack(tmp_path / "pack_two", preset_id="dup", command="two")

    with pytest.raises(ValueError, match="Duplicate preset id"):
        PresetRegistry.discover(tmp_path)


def test_duplicate_commands_fail_clearly(tmp_path):
    write_preset_pack(tmp_path / "pack_one", preset_id="one", command="same")
    write_preset_pack(tmp_path / "pack_two", preset_id="two", command="same")

    with pytest.raises(ValueError, match="Duplicate preset command"):
        PresetRegistry.discover(tmp_path)
