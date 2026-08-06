from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from ..core.effect_schema import BaseEffect
from ..infrastructure.paths import EFFECT_PACKAGE_CACHE_ROOT
from .effect_package_schema import (
    EffectPackageManifest,
    EffectSetManifest,
    HashManifest,
    parse_effect_package_manifest,
    parse_effect_set_manifest,
    parse_hash_manifest,
    validate_manifest_matches_definition,
)
from .effect_preset_registry import EffectPresetDefinition, parse_effect_preset_definitions


_EXTRACTION_LOCK = threading.RLock()


@dataclass(slots=True, frozen=True)
class LoadedEffectPackage:
    manifest: EffectPackageManifest
    effect_class: type[BaseEffect]
    presets: tuple[EffectPresetDefinition, ...]
    extracted_root: Path
    origin_path: str


@dataclass(slots=True, frozen=True)
class LoadedEffectSet:
    manifest: EffectSetManifest
    effects: tuple[LoadedEffectPackage, ...]
    presets: tuple[EffectPresetDefinition, ...]
    extracted_root: Path
    origin_path: str


@dataclass(slots=True, frozen=True)
class PackageVerificationResult:
    ok: bool
    kind: str
    source_id: str | None = None
    package_id: str | None = None
    set_id: str | None = None
    effect_ids: tuple[str, ...] = ()
    preset_ids: tuple[str, ...] = ()


def load_effect_source(path: str | Path) -> LoadedEffectPackage | LoadedEffectSet:
    suffix = Path(path).suffix.lower()
    if suffix == ".lefx":
        return load_effect_package(path)
    if suffix == ".lefxset":
        return load_effect_set(path)
    raise ValueError(f"Unsupported effect source format: {path}")


def load_effect_package(path: str | Path) -> LoadedEffectPackage:
    source_path = Path(path).resolve()
    payload_bytes = source_path.read_bytes()
    return _load_effect_package_bytes(payload_bytes, origin_path=str(source_path))


def load_effect_set(path: str | Path) -> LoadedEffectSet:
    with _EXTRACTION_LOCK:
        return _load_effect_set_locked(path)


def _load_effect_set_locked(path: str | Path) -> LoadedEffectSet:
    source_path = Path(path).resolve()
    payload_bytes = source_path.read_bytes()
    fingerprint = hashlib.sha256(payload_bytes).hexdigest()
    extracted_root = _prepare_extraction_root(fingerprint)
    with zipfile.ZipFile(source_path, "r") as archive:
        _extract_archive(archive, extracted_root)
        hash_manifest = parse_hash_manifest(_read_json(archive, "hashes.json"))
        _verify_archive_hashes(archive, hash_manifest)
        manifest = parse_effect_set_manifest(_read_json(archive, "set-manifest.json"))

        effects: list[LoadedEffectPackage] = []
        for item in manifest.effects:
            file_name = str(item.get("file", "")).strip()
            if not file_name:
                raise ValueError("Effect set manifest contains an effect entry without a file name")
            nested_origin = f"{source_path}!/{file_name}"
            effects.append(_load_effect_package_bytes(archive.read(file_name), origin_path=nested_origin))

    _validate_set_members(manifest, effects)
    presets = tuple(
        preset
        for effect in effects
        for preset in effect.presets
    )
    return LoadedEffectSet(
        manifest=manifest,
        effects=tuple(effects),
        presets=presets,
        extracted_root=extracted_root,
        origin_path=str(source_path),
    )


def inspect_effect_source(path: str | Path) -> dict:
    loaded = load_effect_source(path)
    if isinstance(loaded, LoadedEffectPackage):
        return {
            "kind": "effect_package",
            "source_id": loaded.manifest.source_id,
            "package_id": loaded.manifest.package_id,
            "effect_id": loaded.manifest.effect_id,
            "qualified_effect_id": loaded.manifest.qualified_effect_id,
            "title": loaded.manifest.title,
            "origin_path": loaded.origin_path,
            "presets": [preset.preset_id for preset in loaded.presets],
        }

    return {
        "kind": "effect_set",
        "source_id": loaded.manifest.source_id,
        "set_id": loaded.manifest.set_id,
        "title": loaded.manifest.title,
        "origin_path": loaded.origin_path,
        "effects": [effect.manifest.qualified_effect_id for effect in loaded.effects],
        "presets": [preset.preset_id for preset in loaded.presets],
    }


def verify_effect_source(path: str | Path) -> PackageVerificationResult:
    loaded = load_effect_source(path)
    if isinstance(loaded, LoadedEffectPackage):
        return PackageVerificationResult(
            ok=True,
            kind="effect_package",
            source_id=loaded.manifest.source_id,
            package_id=loaded.manifest.package_id,
            effect_ids=(loaded.manifest.qualified_effect_id,),
            preset_ids=tuple(preset.qualified_preset_id for preset in loaded.presets),
        )

    return PackageVerificationResult(
        ok=True,
        kind="effect_set",
        source_id=loaded.manifest.source_id,
        set_id=loaded.manifest.set_id,
        effect_ids=tuple(effect.manifest.qualified_effect_id for effect in loaded.effects),
        preset_ids=tuple(preset.qualified_preset_id for preset in loaded.presets),
    )


def _load_effect_package_bytes(payload_bytes: bytes, *, origin_path: str) -> LoadedEffectPackage:
    with _EXTRACTION_LOCK:
        return _load_effect_package_bytes_locked(payload_bytes, origin_path=origin_path)


def _load_effect_package_bytes_locked(payload_bytes: bytes, *, origin_path: str) -> LoadedEffectPackage:
    fingerprint = hashlib.sha256(payload_bytes).hexdigest()
    extracted_root = _prepare_extraction_root(fingerprint)
    archive_path = extracted_root / "package.lefx"
    archive_path.write_bytes(payload_bytes)
    with zipfile.ZipFile(archive_path, "r") as archive:
        _extract_archive(archive, extracted_root)
        hash_manifest = parse_hash_manifest(_read_json(archive, "hashes.json"))
        _verify_archive_hashes(archive, hash_manifest)
        manifest = parse_effect_package_manifest(_read_json(archive, "manifest.json"))

        effect_class = _load_effect_class(extracted_root, manifest)
        validate_manifest_matches_definition(manifest, effect_class.get_definition())

        preset_payload = _read_optional_json(archive, "effect-presets.json")
        presets = (
            []
            if preset_payload is None
            else parse_effect_preset_definitions(manifest.source_id, effect_class.get_definition(), preset_payload)
        )

        if _read_optional_json(archive, "commands.json") is not None:
            raise ValueError(
                "LEFX V2 does not support embedded commands.json; use application aliases outside the package"
            )

    return LoadedEffectPackage(
        manifest=manifest,
        effect_class=effect_class,
        presets=tuple(presets),
        extracted_root=extracted_root,
        origin_path=origin_path,
    )


def _prepare_extraction_root(fingerprint: str) -> Path:
    root = EFFECT_PACKAGE_CACHE_ROOT / f"process-{os.getpid()}" / fingerprint
    root.parent.mkdir(parents=True, exist_ok=True)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _extract_archive(archive: zipfile.ZipFile, extracted_root: Path) -> None:
    archive.extractall(extracted_root)


def _read_json(archive: zipfile.ZipFile, name: str) -> dict:
    try:
        with archive.open(name, "r") as handle:
            return json.loads(handle.read().decode("utf-8"))
    except KeyError as exc:
        raise ValueError(f"Archive is missing required file: {name}") from exc


def _read_optional_json(archive: zipfile.ZipFile, name: str) -> dict | None:
    try:
        with archive.open(name, "r") as handle:
            return json.loads(handle.read().decode("utf-8"))
    except KeyError:
        return None


def _verify_archive_hashes(archive: zipfile.ZipFile, hash_manifest: HashManifest) -> None:
    for file_name, expected_digest in hash_manifest.files.items():
        try:
            content = archive.read(file_name)
        except KeyError as exc:
            raise ValueError(f"Archive is missing hashed file: {file_name}") from exc
        actual_digest = hashlib.sha256(content).hexdigest()
        if actual_digest != expected_digest:
            raise ValueError(f"Hash mismatch for {file_name}: expected {expected_digest}, got {actual_digest}")


def _load_effect_class(extracted_root: Path, manifest: EffectPackageManifest) -> type[BaseEffect]:
    if not manifest.entry_module.startswith("payload."):
        raise ValueError(f"Package entry module must be rooted in payload.*, got {manifest.entry_module!r}")
    module_file = extracted_root.joinpath(*manifest.entry_module.split(".")).with_suffix(".py")
    if not module_file.exists():
        raise ValueError(f"Package entry module {manifest.entry_module!r} is missing at {module_file}")

    package_name = f"effectpkg_{hashlib.sha1(str(extracted_root).encode('utf-8')).hexdigest()}"
    payload_root = extracted_root / "payload"
    relative_module = manifest.entry_module.removeprefix("payload.")
    module_name = f"{package_name}.{relative_module}"

    package_module = ModuleType(package_name)
    package_module.__path__ = [str(payload_root)]
    package_module.__package__ = package_name
    sys.modules[package_name] = package_module

    spec = importlib.util.spec_from_file_location(module_name, module_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import package module {manifest.entry_module!r}")

    module = importlib.util.module_from_spec(spec)
    module.__package__ = module_name.rpartition(".")[0]
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    effect_class = getattr(module, manifest.entry_class, None)
    if effect_class is None:
        raise ValueError(f"Package entry class {manifest.entry_class!r} was not found in {manifest.entry_module!r}")
    if not isinstance(effect_class, type) or not issubclass(effect_class, BaseEffect):
        raise ValueError(f"Package entry class {manifest.entry_class!r} is not a BaseEffect subclass")
    return effect_class


def _validate_set_members(
    manifest: EffectSetManifest,
    effects: list[LoadedEffectPackage],
) -> None:
    if not effects:
        raise ValueError("Effect set did not contain any effect packages")

    effect_ids = {effect.manifest.effect_id for effect in effects}
    preset_ids: set[str] = set()
    for effect in effects:
        if effect.manifest.source_id != manifest.source_id:
            raise ValueError(
                f"Effect package source_id {effect.manifest.source_id!r} does not match set source_id {manifest.source_id!r}"
            )
        for preset in effect.presets:
            if preset.preset_id in effect_ids:
                raise ValueError(
                    f"Preset id {preset.preset_id!r} collides with an effect id "
                    f"within set source {manifest.source_id!r}"
                )
            if preset.preset_id in preset_ids:
                raise ValueError(f"Duplicate preset id detected within set source {manifest.source_id!r}: {preset.preset_id!r}")
            preset_ids.add(preset.preset_id)
