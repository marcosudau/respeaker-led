from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from ..core.effect_schema import BaseEffect
from .effect_command_registry import parse_command_definitions
from .effect_package_schema import EffectPackageManifest, EffectSetManifest, load_source_manifest, serialize_effect_definition


@dataclass(slots=True, frozen=True)
class BuiltArtifact:
    kind: str
    output_path: Path
    identifier: str


def build_effect_package(source_dir: str | Path, output_path: str | Path) -> BuiltArtifact:
    built = _build_effect_package_bytes(Path(source_dir))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(built["bytes"])
    return BuiltArtifact(kind="effect_package", output_path=output.resolve(), identifier=built["manifest"].qualified_effect_id)


def build_effect_set(source_dir: str | Path, output_path: str | Path) -> BuiltArtifact:
    built = _build_effect_set_bytes(Path(source_dir))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(built["bytes"])
    return BuiltArtifact(kind="effect_set", output_path=output.resolve(), identifier=built["manifest"].set_id)


def _build_effect_package_bytes(source_dir: Path) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    metadata = load_source_manifest(source_dir, "effect")
    entry_file = source_dir / str(metadata.get("entry_file", "effect.py"))
    if not entry_file.exists():
        raise FileNotFoundError(f"Effect source is missing entry file: {entry_file}")
    effect_class = _load_effect_class(source_dir, entry_file, metadata.get("entry_class"))
    definition = effect_class.get_definition()
    serialized = serialize_effect_definition(definition)
    source_id = str(metadata.get("source_id", "")).strip()
    if not source_id:
        raise ValueError("Effect source manifest must define source_id")
    package_id = str(metadata.get("package_id", f"{source_id}.{definition.id}")).strip()
    min_service_version = str(metadata.get("min_service_version", "1.0.0")).strip()
    entry_module = f"payload.{entry_file.relative_to(source_dir).with_suffix('').as_posix().replace('/', '.')}"
    manifest = EffectPackageManifest(
        format="lefx/1",
        package_id=package_id,
        source_id=source_id,
        effect_id=definition.id,
        qualified_effect_id=f"{source_id}::{definition.id}",
        title=definition.title,
        description=definition.description,
        version=int(definition.version),
        runtime="python_base_effect/1",
        entry_module=entry_module,
        entry_class=effect_class.__name__,
        defaults=serialized["defaults"],
        parameter_schema=serialized["parameter_schema"],
        layer_rules=serialized["layer_rules"],
        capabilities=serialized["capabilities"],
        min_service_version=min_service_version,
        tags=tuple(serialized["tags"]),
        author=None if metadata.get("author") is None else str(metadata.get("author")),
        vendor=None if metadata.get("vendor") is None else str(metadata.get("vendor")),
    )
    files = _collect_payload_files(source_dir)
    archive_bytes = _build_effect_archive(manifest, files)
    return {"bytes": archive_bytes, "manifest": manifest}


def _build_effect_set_bytes(source_dir: Path) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    metadata = load_source_manifest(source_dir, "set")
    source_id = str(metadata.get("source_id", "")).strip()
    if not source_id:
        raise ValueError("Effect set source manifest must define source_id")
    set_id = str(metadata.get("set_id", "")).strip()
    if not set_id:
        raise ValueError("Effect set source manifest must define set_id")

    effects_root = source_dir / "effects"
    if not effects_root.exists():
        raise FileNotFoundError(f"Effect set source is missing effects directory: {effects_root}")

    selected_effects = metadata.get("effects")
    if isinstance(selected_effects, list) and selected_effects:
        effect_dirs = [effects_root / str(item) for item in selected_effects]
    else:
        effect_dirs = sorted(path for path in effects_root.iterdir() if path.is_dir())
    if not effect_dirs:
        raise ValueError(f"Effect set source {source_dir} does not define any effect directories")

    nested_packages: list[tuple[str, bytes, EffectPackageManifest]] = []
    for effect_dir in effect_dirs:
        built = _build_effect_package_bytes(effect_dir)
        file_name = f"effects/{effect_dir.name}.lefx"
        nested_packages.append((file_name, built["bytes"], built["manifest"]))

    commands_path = source_dir / "commands.json"
    if not commands_path.exists():
        raise FileNotFoundError(f"Effect set source is missing commands.json: {commands_path}")
    commands_payload = json.loads(commands_path.read_text(encoding="utf-8"))
    parse_command_definitions(source_id, commands_payload)

    effect_entries = [
        {
            "file": file_name,
            "package_id": manifest.package_id,
            "effect_id": manifest.effect_id,
            "qualified_effect_id": manifest.qualified_effect_id,
            "version": manifest.version,
        }
        for file_name, _, manifest in nested_packages
    ]
    manifest = EffectSetManifest(
        format="lefxset/1",
        set_id=set_id,
        source_id=source_id,
        title=str(metadata.get("title", set_id)).strip(),
        version=int(metadata.get("version", 1)),
        min_service_version=str(metadata.get("min_service_version", "1.0.0")).strip(),
        effects=tuple(effect_entries),
        description=None if metadata.get("description") is None else str(metadata.get("description")),
        tags=tuple(str(item) for item in metadata.get("tags", [])) if isinstance(metadata.get("tags"), list) else (),
        author=None if metadata.get("author") is None else str(metadata.get("author")),
        vendor=None if metadata.get("vendor") is None else str(metadata.get("vendor")),
        command_namespace=None if metadata.get("command_namespace") is None else str(metadata.get("command_namespace")),
    )
    archive_bytes = _build_effect_set_archive(manifest, nested_packages, commands_payload)
    return {"bytes": archive_bytes, "manifest": manifest}


def _load_effect_class(source_dir: Path, entry_file: Path, configured_entry_class: str | None) -> type[BaseEffect]:
    unique_name = f"effectsrc_{hashlib.sha1(str(source_dir).encode('utf-8')).hexdigest()}_{entry_file.stem}"
    spec = importlib.util.spec_from_file_location(unique_name, entry_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import source effect module from {entry_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
    spec.loader.exec_module(module)

    if configured_entry_class:
        effect_class = getattr(module, str(configured_entry_class), None)
        if not isinstance(effect_class, type) or not issubclass(effect_class, BaseEffect):
            raise ValueError(f"Configured entry_class {configured_entry_class!r} is not a BaseEffect subclass")
        return effect_class

    discovered = [
        value for value in module.__dict__.values()
        if isinstance(value, type) and issubclass(value, BaseEffect) and value is not BaseEffect
    ]
    if len(discovered) != 1:
        raise ValueError(f"Source effect module {entry_file} must contain exactly one BaseEffect subclass when entry_class is omitted")
    return discovered[0]


def _collect_payload_files(source_dir: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {"payload/__init__.py": b""}
    for path in sorted(source_dir.rglob("*")):
        if path.is_dir():
            continue
        if "__pycache__" in path.parts:
            continue
        if path.name in {"effect.json", "effect.yaml"}:
            continue
        relative = path.relative_to(source_dir).as_posix()
        destination = f"payload/{relative}"
        files[destination] = path.read_bytes()
        if path.suffix == ".py":
            parent_parts = list(Path(destination).parent.parts)
            while parent_parts:
                init_path = "/".join(parent_parts + ["__init__.py"])
                files.setdefault(init_path, b"")
                parent_parts.pop()
    return files


def _build_effect_archive(manifest: EffectPackageManifest, files: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest_bytes = json.dumps(manifest.to_dict(), ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
        archive.writestr("manifest.json", manifest_bytes)
        hashes = {"manifest.json": hashlib.sha256(manifest_bytes).hexdigest()}
        for name, content in files.items():
            archive.writestr(name, content)
            hashes[name] = hashlib.sha256(content).hexdigest()
        hash_bytes = json.dumps({"algorithm": "sha256", "files": hashes}, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
        archive.writestr("hashes.json", hash_bytes)
    return buffer.getvalue()


def _build_effect_set_archive(
    manifest: EffectSetManifest,
    nested_packages: list[tuple[str, bytes, EffectPackageManifest]],
    commands_payload: dict[str, Any],
) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest_bytes = json.dumps(manifest.to_dict(), ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
        archive.writestr("set-manifest.json", manifest_bytes)
        hashes = {"set-manifest.json": hashlib.sha256(manifest_bytes).hexdigest()}
        command_bytes = json.dumps(commands_payload, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
        archive.writestr("commands.json", command_bytes)
        hashes["commands.json"] = hashlib.sha256(command_bytes).hexdigest()
        for file_name, payload, _ in nested_packages:
            archive.writestr(file_name, payload)
            hashes[file_name] = hashlib.sha256(payload).hexdigest()
        hash_bytes = json.dumps({"algorithm": "sha256", "files": hashes}, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
        archive.writestr("hashes.json", hash_bytes)
    return buffer.getvalue()
