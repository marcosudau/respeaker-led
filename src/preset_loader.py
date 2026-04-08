from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

from .models import DiscoveredPreset, PresetManifest
from .paths import PRESET_PACKS_ROOT
from .simple_yaml import parse_simple_yaml


REQUIRED_MANIFEST_KEYS = {"id", "name", "description", "command"}


def _load_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load preset module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _read_manifest(manifest_path: Path) -> PresetManifest:
    raw = parse_simple_yaml(manifest_path.read_text(encoding="utf-8"))
    missing = REQUIRED_MANIFEST_KEYS - set(raw.keys())
    if missing:
        raise ValueError(f"Preset manifest {manifest_path} is missing keys: {', '.join(sorted(missing))}")

    tags = raw.get("tags", [])
    if not isinstance(tags, list):
        tags = [str(tags)]

    return PresetManifest(
        preset_id=str(raw["id"]),
        name=str(raw["name"]),
        description=str(raw["description"]),
        command=str(raw["command"]),
        target_layer=str(raw.get("target_layer", "main_layer")),
        supports_cli=bool(raw.get("supports_cli", True)),
        supports_api=bool(raw.get("supports_api", True)),
        sample_spec=str(raw["sample_spec"]) if raw.get("sample_spec") else None,
        tags=[str(item) for item in tags],
    )


@dataclass(slots=True)
class PresetRegistry:
    presets_by_id: dict[str, DiscoveredPreset]
    presets_by_command: dict[str, DiscoveredPreset]

    @classmethod
    def empty(cls) -> "PresetRegistry":
        return cls(presets_by_id={}, presets_by_command={})

    @classmethod
    def discover(cls, presets_root: Path | None = None) -> "PresetRegistry":
        presets_root = presets_root or PRESET_PACKS_ROOT
        if not presets_root.exists():
            return cls.empty()

        presets_by_id: dict[str, DiscoveredPreset] = {}
        presets_by_command: dict[str, DiscoveredPreset] = {}

        for folder in sorted(path for path in presets_root.iterdir() if path.is_dir()):
            manifest_path = folder / "preset.yaml"
            module_path = folder / "preset.py"
            if not manifest_path.exists() or not module_path.exists():
                continue

            manifest = _read_manifest(manifest_path)
            module_name = f"respeaker_preset_{manifest.preset_id}"
            module = _load_module(module_path, module_name)
            build_preset = getattr(module, "build_preset", None)
            if not callable(build_preset):
                raise ValueError(f"Preset module {module_path} does not expose build_preset(spec)")

            sample_path = folder / manifest.sample_spec if manifest.sample_spec else None
            preset = DiscoveredPreset(
                manifest=manifest,
                folder=folder,
                module_path=module_path,
                sample_path=sample_path if sample_path and sample_path.exists() else None,
                build_preset=build_preset,
            )

            if manifest.preset_id in presets_by_id:
                raise ValueError(f"Duplicate preset id detected: {manifest.preset_id}")
            if manifest.command in presets_by_command:
                raise ValueError(f"Duplicate preset command detected: {manifest.command}")

            presets_by_id[manifest.preset_id] = preset
            presets_by_command[manifest.command] = preset

        return cls(presets_by_id=presets_by_id, presets_by_command=presets_by_command)

    def list_presets(self) -> list[DiscoveredPreset]:
        return [self.presets_by_id[key] for key in sorted(self.presets_by_id)]

    def get_by_id(self, preset_id: str) -> DiscoveredPreset:
        return self.presets_by_id[preset_id]

    def get_by_command(self, command: str) -> DiscoveredPreset:
        return self.presets_by_command[command]
