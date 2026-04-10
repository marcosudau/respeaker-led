from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ..core.effect_schema import BaseEffect
from ..infrastructure.paths import EFFECT_PACKAGE_CACHE_ROOT
from .effect_command_registry import EffectCommandDefinition, parse_command_definitions
from .effect_package_schema import (
    EffectPackageManifest,
    EffectSetManifest,
    HashManifest,
    parse_effect_package_manifest,
    parse_effect_set_manifest,
    parse_hash_manifest,
    validate_manifest_matches_definition,
)


@dataclass(slots=True, frozen=True)
class LoadedEffectPackage:
    manifest: EffectPackageManifest
    effect_class: type[BaseEffect]
    extracted_root: Path
    origin_path: str


@dataclass(slots=True, frozen=True)
class LoadedEffectSet:
    manifest: EffectSetManifest
    effects: tuple[LoadedEffectPackage, ...]
    commands: tuple[EffectCommandDefinition, ...]
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
    command_names: tuple[str, ...] = ()


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

        commands_payload = _read_json(archive, "commands.json")
        commands = tuple(parse_command_definitions(manifest.source_id, commands_payload))
        _validate_set_members(manifest, effects, commands)

    return LoadedEffectSet(
        manifest=manifest,
        effects=tuple(effects),
        commands=commands,
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
        }

    return {
        "kind": "effect_set",
        "source_id": loaded.manifest.source_id,
        "set_id": loaded.manifest.set_id,
        "title": loaded.manifest.title,
        "origin_path": loaded.origin_path,
        "effects": [effect.manifest.qualified_effect_id for effect in loaded.effects],
        "commands": [command.command_name for command in loaded.commands],
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
        )

    return PackageVerificationResult(
        ok=True,
        kind="effect_set",
        source_id=loaded.manifest.source_id,
        set_id=loaded.manifest.set_id,
        effect_ids=tuple(effect.manifest.qualified_effect_id for effect in loaded.effects),
        command_names=tuple(command.command_name for command in loaded.commands),
    )


def _load_effect_package_bytes(payload_bytes: bytes, *, origin_path: str) -> LoadedEffectPackage:
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
    return LoadedEffectPackage(
        manifest=manifest,
        effect_class=effect_class,
        extracted_root=extracted_root,
        origin_path=origin_path,
    )


def _prepare_extraction_root(fingerprint: str) -> Path:
    root = EFFECT_PACKAGE_CACHE_ROOT / fingerprint
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

    unique_name = f"effectpkg_{hashlib.sha1(str(extracted_root).encode('utf-8')).hexdigest()}_{manifest.entry_module.replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(unique_name, module_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import package module {manifest.entry_module!r}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
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
    commands: tuple[EffectCommandDefinition, ...],
) -> None:
    qualified_ids = {effect.manifest.qualified_effect_id for effect in effects}
    if not qualified_ids:
        raise ValueError("Effect set did not contain any effect packages")
    for effect in effects:
        if effect.manifest.source_id != manifest.source_id:
            raise ValueError(
                f"Effect package source_id {effect.manifest.source_id!r} does not match set source_id {manifest.source_id!r}"
            )
    for command in commands:
        for action in (command.on_action, command.off_action):
            if action is None or action.action != "apply_effect":
                continue
            if action.effect_id not in qualified_ids:
                raise ValueError(
                    f"Command {command.command_name!r} references unknown effect {action.effect_id!r} in set {manifest.set_id!r}"
                )
