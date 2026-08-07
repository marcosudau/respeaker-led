from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from types import ModuleType
from typing import Any

from ..core.effect_schema import (
    BaseEffect,
    DefinitionType,
    OverlayMode,
    validate_definition_contract,
)
from ..core.parameter_validation import resolve_configuration
from .effect_package_loader import load_effect_package
from .effect_package_schema import (
    EffectPackageManifest,
    EffectSetManifest,
    load_optional_source_manifest,
    load_source_manifest,
    serialize_effect_definition,
)
from .effect_preset_registry import EffectPresetDefinition, parse_effect_preset_definitions


_ALLOWED_EFFECT_IMPORTS = {
    "__future__",
    "collections",
    "dataclasses",
    "enum",
    "functools",
    "hashlib",
    "itertools",
    "math",
    "random",
    "statistics",
    "typing",
    "respeaker_led.core.color_math",
    "respeaker_led.core.effect_schema",
    "src.core.color_math",
    "src.core.effect_schema",
}


@dataclass(slots=True, frozen=True)
class BuiltArtifact:
    kind: str
    output_path: Path
    identifier: str
    warnings: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class ValidationResult:
    kind: str
    identifier: str
    source_id: str
    warnings: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ScaffoldResult:
    kind: str
    target_path: Path
    created_files: tuple[str, ...]


def build_effect_package(source_dir: str | Path, output_path: str | Path) -> BuiltArtifact:
    built = _build_effect_package_bytes(Path(source_dir))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(built["bytes"])
    return BuiltArtifact(
        kind="effect_package",
        output_path=output.resolve(),
        identifier=built["manifest"].qualified_effect_id,
        warnings=tuple(built["warnings"]),
    )


def build_effect_set(source_dir: str | Path, output_path: str | Path) -> BuiltArtifact:
    built = _build_effect_set_bytes(Path(source_dir))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(built["bytes"])
    return BuiltArtifact(
        kind="effect_set",
        output_path=output.resolve(),
        identifier=built["manifest"].set_id,
        warnings=tuple(built["warnings"]),
    )


def validate_effect_source(source_dir: str | Path) -> ValidationResult:
    built = _build_effect_package_bytes(Path(source_dir))
    manifest: EffectPackageManifest = built["manifest"]
    return ValidationResult(
        kind="effect_source",
        identifier=manifest.qualified_effect_id,
        source_id=manifest.source_id,
        warnings=tuple(built["warnings"]),
        details={
            "package_id": manifest.package_id,
            "entry_module": manifest.entry_module,
            "entry_class": manifest.entry_class,
            "preset_count": len(built["presets"]),
        },
    )


def validate_effect_set_source(source_dir: str | Path) -> ValidationResult:
    built = _build_effect_set_bytes(Path(source_dir))
    manifest: EffectSetManifest = built["manifest"]
    return ValidationResult(
        kind="effect_set_source",
        identifier=manifest.set_id,
        source_id=manifest.source_id,
        warnings=tuple(built["warnings"]),
        details={
            "effect_count": len(manifest.effects),
            "preset_count": built["preset_count"],
        },
    )


def init_effect_source(
    target_dir: str | Path,
    *,
    effect_id: str,
    source_id: str,
    title: str | None = None,
    package_id: str | None = None,
    class_name: str | None = None,
    definition_type: str = "state",
    overlay_mode: str | None = None,
    format_name: str = "yaml",
    force: bool = False,
) -> ScaffoldResult:
    target = Path(target_dir).resolve()
    if target.exists() and any(target.iterdir()) and not force:
        raise FileExistsError(f"Target directory already exists and is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)

    normalized_title = title or _title_from_effect_id(effect_id)
    normalized_package_id = package_id or f"{source_id}.{effect_id}"
    normalized_class_name = class_name or _class_name_from_effect_id(effect_id)

    metadata_path = _effect_manifest_path(target, format_name)
    metadata_text = _render_effect_metadata(
        format_name=format_name,
        package_id=normalized_package_id,
        source_id=source_id,
        class_name=normalized_class_name,
        title=normalized_title,
        definition_type=definition_type,
        overlay_mode=overlay_mode,
    )
    effect_py = _render_effect_python(
        class_name=normalized_class_name,
        effect_id=effect_id,
        title=normalized_title,
        definition_type=definition_type,
        overlay_mode=overlay_mode,
    )
    preset_text = _render_effect_presets_template(title=normalized_title, effect_id=effect_id)

    created_files = [
        _write_text_file(metadata_path, metadata_text),
        _write_text_file(target / "presets.yaml", preset_text),
        _write_text_file(target / "effect.py", effect_py),
    ]
    (target / "assets").mkdir(exist_ok=True)
    (target / "extra").mkdir(exist_ok=True)
    created_files.append(_write_text_file(target / "extra" / "__init__.py", "from __future__ import annotations\n"))
    return ScaffoldResult(kind="effect_source", target_path=target, created_files=tuple(created_files))


def init_effect_set_source(
    target_dir: str | Path,
    *,
    set_id: str,
    source_id: str,
    title: str | None = None,
    format_name: str = "yaml",
    force: bool = False,
) -> ScaffoldResult:
    target = Path(target_dir).resolve()
    if target.exists() and any(target.iterdir()) and not force:
        raise FileExistsError(f"Target directory already exists and is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)

    normalized_title = title or _title_from_effect_id(set_id)
    metadata_path = _set_manifest_path(target, format_name)
    metadata_text = _render_set_metadata(
        format_name=format_name,
        set_id=set_id,
        source_id=source_id,
        title=normalized_title,
    )

    created_files = [_write_text_file(metadata_path, metadata_text)]
    (target / "effects").mkdir(exist_ok=True)
    return ScaffoldResult(kind="effect_set_source", target_path=target, created_files=tuple(created_files))


def init_effect_batch(batch_file: str | Path, output_root: str | Path, *, force: bool = False) -> list[ScaffoldResult]:
    batch_path = Path(batch_file).resolve()
    output_dir = Path(output_root).resolve()
    payload = json.loads(batch_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Effect batch file must contain a JSON object")
    _reject_unknown_source_keys(payload, {"source_id", "effects"}, "effect batch")
    source_id = str(payload.get("source_id", "")).strip()
    if not source_id:
        raise ValueError("Effect batch file must define source_id")
    raw_effects = payload.get("effects")
    if not isinstance(raw_effects, list) or not raw_effects:
        raise ValueError("Effect batch file must define a non-empty effects list")

    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[ScaffoldResult] = []
    for item in raw_effects:
        if not isinstance(item, dict):
            raise ValueError("Each effect batch item must be a JSON object")
        _reject_unknown_source_keys(
            item,
            {
                "effect_id",
                "title",
                "package_id",
                "class_name",
                "definition_type",
                "overlay_mode",
                "format",
            },
            "effect batch item",
        )
        effect_id = str(item.get("effect_id", "")).strip()
        if not effect_id:
            raise ValueError("Each effect batch item must define effect_id")
        results.append(
            init_effect_source(
                output_dir / effect_id,
                effect_id=effect_id,
                source_id=source_id,
                title=None if item.get("title") is None else str(item.get("title")),
                package_id=None if item.get("package_id") is None else str(item.get("package_id")),
                class_name=None if item.get("class_name") is None else str(item.get("class_name")),
                definition_type=str(item.get("definition_type", "state")),
                overlay_mode=None if item.get("overlay_mode") is None else str(item.get("overlay_mode")),
                format_name=str(item.get("format", "yaml")),
                force=force,
            )
        )
    return results


def _build_effect_package_bytes(source_dir: Path) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    metadata = load_source_manifest(source_dir, "effect")
    _reject_unknown_source_keys(
        metadata,
        {
            "package_id",
            "source_id",
            "entry_file",
            "entry_class",
            "min_service_version",
            "author",
            "vendor",
        },
        "effect source manifest",
    )
    entry_file = source_dir / str(metadata.get("entry_file", "effect.py"))
    if not entry_file.exists():
        raise FileNotFoundError(f"Effect source is missing entry file: {entry_file}")

    _validate_effect_source_layout(source_dir, entry_file)
    effect_class = _load_effect_class(source_dir, entry_file, metadata.get("entry_class"))
    definition = effect_class.get_definition()
    validate_definition_contract(definition)
    resolve_configuration(definition)
    serialized = serialize_effect_definition(definition)
    source_id = str(metadata.get("source_id", "")).strip()
    if not source_id:
        raise ValueError("Effect source manifest must define source_id")
    package_id = str(metadata.get("package_id", f"{source_id}.{definition.id}")).strip()
    min_service_version = str(metadata.get("min_service_version", "1.0.0")).strip()
    entry_module = f"payload.{entry_file.relative_to(source_dir).with_suffix('').as_posix().replace('/', '.')}"
    manifest = EffectPackageManifest(
        format="lefx/2",
        package_id=package_id,
        source_id=source_id,
        effect_id=definition.id,
        qualified_effect_id=f"{source_id}::{definition.id}",
        title=definition.title,
        description=definition.description,
        definition_type=definition.definition_type,
        overlay_mode=definition.overlay_mode,
        version=int(definition.version),
        runtime="python_base_effect/1",
        entry_module=entry_module,
        entry_class=effect_class.__name__,
        defaults=serialized["defaults"],
        parameter_schema=serialized["parameter_schema"],
        runtime_input_schema=serialized["runtime_input_schema"],
        visual=serialized["visual"],
        input_sampling=serialized["input_sampling"],
        layer_rules=serialized["layer_rules"],
        capabilities=serialized["capabilities"],
        min_service_version=min_service_version,
        tags=tuple(serialized["tags"]),
        author=None if metadata.get("author") is None else str(metadata.get("author")),
        vendor=None if metadata.get("vendor") is None else str(metadata.get("vendor")),
    )

    presets_payload = load_optional_source_manifest(source_dir, "presets")
    presets = (
        []
        if presets_payload is None
        else parse_effect_preset_definitions(source_id, definition, presets_payload)
    )

    if (source_dir / "commands.json").exists():
        raise ValueError(
            "LEFX V2 does not support embedded commands.json; use application aliases outside the package"
        )

    files = _collect_payload_files(source_dir)
    archive_bytes = _build_effect_archive(manifest, files, presets=presets)
    return {
        "bytes": archive_bytes,
        "manifest": manifest,
        "presets": presets,
        "warnings": [],
    }


def _build_effect_set_bytes(source_dir: Path) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    metadata = load_source_manifest(source_dir, "set")
    _reject_unknown_source_keys(
        metadata,
        {
            "set_id",
            "source_id",
            "title",
            "version",
            "min_service_version",
            "effects",
            "description",
            "tags",
            "author",
            "vendor",
        },
        "effect set source manifest",
    )
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
        effect_items = [_resolve_effect_set_member(effects_root, str(item)) for item in selected_effects]
    else:
        effect_items = sorted(
            [path for path in effects_root.iterdir() if path.is_dir() or path.suffix.lower() == ".lefx"],
            key=lambda path: path.name,
        )
    if not effect_items:
        raise ValueError(f"Effect set source {source_dir} does not define any effect members")

    nested_packages: list[tuple[str, bytes, EffectPackageManifest]] = []
    warnings: list[str] = []
    preset_ids: set[str] = set()
    preset_count = 0

    for item in effect_items:
        if item.is_dir():
            built = _build_effect_package_bytes(item)
            file_name = f"effects/{item.name}.lefx"
            manifest = built["manifest"]
            if manifest.source_id != source_id:
                raise ValueError(
                    f"Effect package {item.name!r} has source_id {manifest.source_id!r}, expected {source_id!r}"
                )
            warnings.append(
                f"Effect set member {item.name!r} was built from a source directory. Prefer prebuilt .lefx files for set assembly."
            )
            nested_packages.append((file_name, built["bytes"], manifest))
            preset_count += _track_preset_ids(preset_ids, built["presets"])
            continue

        loaded = load_effect_package(item)
        if loaded.manifest.source_id != source_id:
            raise ValueError(
                f"Effect package {item.name!r} has source_id {loaded.manifest.source_id!r}, expected {source_id!r}"
            )
        nested_packages.append((f"effects/{item.name}", item.read_bytes(), loaded.manifest))
        preset_count += _track_preset_ids(preset_ids, list(loaded.presets))

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
        format="lefxset/2",
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
    )
    archive_bytes = _build_effect_set_archive(manifest, nested_packages)
    return {
        "bytes": archive_bytes,
        "manifest": manifest,
        "warnings": warnings,
        "preset_count": preset_count,
    }


def _track_preset_ids(seen: set[str], presets: list[EffectPresetDefinition]) -> int:
    for preset in presets:
        if preset.preset_id in seen:
            raise ValueError(f"Duplicate preset id detected within source: {preset.preset_id!r}")
        seen.add(preset.preset_id)
    return len(presets)


def _reject_unknown_source_keys(
    payload: dict[str, Any],
    allowed: set[str],
    label: str,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"{label} contains unknown keys: {', '.join(unknown)}")


def _resolve_effect_set_member(effects_root: Path, raw_name: str) -> Path:
    candidate = effects_root / raw_name
    if candidate.exists():
        return candidate
    lefx_candidate = effects_root / f"{raw_name}.lefx"
    if lefx_candidate.exists():
        return lefx_candidate
    raise FileNotFoundError(f"Effect set member could not be resolved: {raw_name}")


def _load_effect_class(source_dir: Path, entry_file: Path, configured_entry_class: str | None) -> type[BaseEffect]:
    package_name = f"effectsrc_{hashlib.sha1(str(source_dir).encode('utf-8')).hexdigest()}"
    relative_module = ".".join(entry_file.relative_to(source_dir).with_suffix("").parts)
    module_name = f"{package_name}.{relative_module}"

    package_module = ModuleType(package_name)
    package_module.__path__ = [str(source_dir)]
    package_module.__package__ = package_name
    sys.modules[package_name] = package_module

    spec = importlib.util.spec_from_file_location(module_name, entry_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import source effect module from {entry_file}")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = module_name.rpartition(".")[0]
    sys.modules[module_name] = module
    import respeaker_led
    import respeaker_led.core.color_math
    import respeaker_led.core.effect_schema
    sys.modules.setdefault("src", respeaker_led)
    sys.modules.setdefault("src.core", respeaker_led.core)
    sys.modules.setdefault("src.core.effect_schema", respeaker_led.core.effect_schema)
    sys.modules.setdefault("src.core.color_math", respeaker_led.core.color_math)

    spec.loader.exec_module(module)

    discovered = [
        value for value in module.__dict__.values()
        if (
            isinstance(value, type)
            and issubclass(value, BaseEffect)
            and value is not BaseEffect
            and value.__module__ == module.__name__
        )
    ]
    if len(discovered) != 1:
        raise ValueError(
            f"Source effect module {entry_file} must contain exactly one local BaseEffect subclass"
        )

    if configured_entry_class:
        effect_class = getattr(module, str(configured_entry_class), None)
        if not isinstance(effect_class, type) or not issubclass(effect_class, BaseEffect):
            raise ValueError(f"Configured entry_class {configured_entry_class!r} is not a BaseEffect subclass")
        if effect_class is not discovered[0]:
            raise ValueError(
                f"Configured entry_class {configured_entry_class!r} is not the single local effect class"
            )
        return effect_class

    return discovered[0]


def _validate_effect_source_layout(source_dir: Path, entry_file: Path) -> None:
    try:
        entry_file.relative_to(source_dir)
    except ValueError as exc:
        raise ValueError("Effect entry_file must stay inside its source directory") from exc

    python_files = sorted(source_dir.rglob("*.py"))
    common_files = [path for path in python_files if path.name.casefold() == "common.py"]
    if common_files:
        names = ", ".join(path.relative_to(source_dir).as_posix() for path in common_files)
        raise ValueError(
            f"LEFX V2 sources must not contain generic common.py modules: {names}"
        )

    for path in python_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    continue
                modules = [] if node.module is None else [node.module]
            else:
                continue
            for module in modules:
                if _effect_import_is_allowed(module):
                    continue
                raise ValueError(
                    f"LEFX V2 source {path.relative_to(source_dir).as_posix()} "
                    f"imports unsupported module {module!r}"
                )


def _effect_import_is_allowed(module: str) -> bool:
    return any(
        module == allowed or module.startswith(f"{allowed}.")
        for allowed in _ALLOWED_EFFECT_IMPORTS
    )


def _collect_payload_files(source_dir: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {"payload/__init__.py": b""}
    for path in sorted(source_dir.rglob("*")):
        if path.is_dir():
            continue
        if "__pycache__" in path.parts:
            continue
        if path.name in {"effect.json", "effect.yaml", "presets.json", "presets.yaml", "commands.json"}:
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
    # Synthesized __init__.py entries land in discovery order, so sort the whole
    # mapping to keep the archive layout independent of the traversal.
    return dict(sorted(files.items()))


# Archives are tracked in git, so a rebuild must not change their bytes when the
# sources did not. writestr() with a plain name stamps every entry with the
# current time and derives create_system from the build host, which made each
# build rewrite every .lefx and .lefxset with identical content.
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_ZIP_FILE_ATTRIBUTES = 0o644 << 16
_ZIP_CREATE_SYSTEM = 3  # Unix, so archives do not differ between Windows and Linux builds


def _write_archive_entry(archive: zipfile.ZipFile, name: str, content: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = _ZIP_FILE_ATTRIBUTES
    info.create_system = _ZIP_CREATE_SYSTEM
    archive.writestr(info, content)


def _build_effect_archive(
    manifest: EffectPackageManifest,
    files: dict[str, bytes],
    *,
    presets: list[EffectPresetDefinition],
) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest_bytes = json.dumps(manifest.to_dict(), ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
        _write_archive_entry(archive, "manifest.json", manifest_bytes)
        hashes = {"manifest.json": hashlib.sha256(manifest_bytes).hexdigest()}

        if presets:
            preset_bytes = json.dumps(
                {"presets": {preset.preset_id: _serialize_preset_payload(preset) for preset in presets}},
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            ).encode("utf-8")
            _write_archive_entry(archive, "effect-presets.json", preset_bytes)
            hashes["effect-presets.json"] = hashlib.sha256(preset_bytes).hexdigest()

        for name, content in sorted(files.items()):
            _write_archive_entry(archive, name, content)
            hashes[name] = hashlib.sha256(content).hexdigest()

        hash_bytes = json.dumps({"algorithm": "sha256", "files": hashes}, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
        _write_archive_entry(archive, "hashes.json", hash_bytes)
    return buffer.getvalue()


def _serialize_preset_payload(preset: EffectPresetDefinition) -> dict[str, Any]:
    payload = {
        "params": dict(preset.params),
        "tags": list(preset.tags),
    }
    if preset.title is not None:
        payload["title"] = preset.title
    if preset.description is not None:
        payload["description"] = preset.description
    return payload


def _build_effect_set_archive(
    manifest: EffectSetManifest,
    nested_packages: list[tuple[str, bytes, EffectPackageManifest]],
) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest_bytes = json.dumps(manifest.to_dict(), ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
        _write_archive_entry(archive, "set-manifest.json", manifest_bytes)
        hashes = {"set-manifest.json": hashlib.sha256(manifest_bytes).hexdigest()}
        # Member order follows the source manifest and mirrors effect_entries,
        # so it is deliberate and must not be re-sorted here.
        for file_name, payload, _ in nested_packages:
            _write_archive_entry(archive, file_name, payload)
            hashes[file_name] = hashlib.sha256(payload).hexdigest()
        hash_bytes = json.dumps({"algorithm": "sha256", "files": hashes}, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
        _write_archive_entry(archive, "hashes.json", hash_bytes)
    return buffer.getvalue()


def _effect_manifest_path(target: Path, format_name: str) -> Path:
    normalized = format_name.strip().lower()
    if normalized not in {"yaml", "json"}:
        raise ValueError(f"Unsupported format: {format_name!r}")
    return target / f"effect.{normalized}"


def _set_manifest_path(target: Path, format_name: str) -> Path:
    normalized = format_name.strip().lower()
    if normalized not in {"yaml", "json"}:
        raise ValueError(f"Unsupported format: {format_name!r}")
    return target / f"set.{normalized}"


def _render_effect_metadata(
    *,
    format_name: str,
    package_id: str,
    source_id: str,
    class_name: str,
    title: str,
    definition_type: str,
    overlay_mode: str | None,
) -> str:
    normalized = format_name.strip().lower()
    if normalized == "json":
        return json.dumps(
            {
                "package_id": package_id,
                "source_id": source_id,
                "entry_class": class_name,
                "min_service_version": "1.0.0",
                "notes": {
                    "title_hint": title,
                    "definition_type": definition_type,
                    "overlay_mode": overlay_mode,
                },
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        ) + "\n"
    return "\n".join(
        [
            "# Primary metadata for this effect source.",
            f"# Title hint: {title}",
            f"# Definition type: {definition_type}",
            f"# Overlay mode: {overlay_mode or 'not-applicable'}",
            f"package_id: {package_id}",
            f"source_id: {source_id}",
            f"entry_class: {class_name}",
            "min_service_version: 1.0.0",
            "",
        ]
    )


def _render_set_metadata(*, format_name: str, set_id: str, source_id: str, title: str) -> str:
    normalized = format_name.strip().lower()
    if normalized == "json":
        return json.dumps(
            {
                "set_id": set_id,
                "source_id": source_id,
                "title": title,
                "version": 1,
                "min_service_version": "1.0.0",
                "effects": [],
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        ) + "\n"
    return "\n".join(
        [
            "# Metadata for this effect set source.",
            f"set_id: {set_id}",
            f"source_id: {source_id}",
            f"title: {title}",
            "version: 1",
            "min_service_version: 1.0.0",
            "effects:",
            "  # - add prebuilt .lefx file names here",
            "",
        ]
    )


def _render_effect_presets_template(*, title: str, effect_id: str) -> str:
    preset_id = f"{effect_id}_example"
    return "\n".join(
        [
            "# Optional embedded presets for this effect.",
            "# Presets configure this definition and cannot change its type or lifecycle.",
            "presets:",
            f"  {preset_id}:",
            f"    title: {json.dumps(f'{title} Example', ensure_ascii=True)}",
            f"    description: {json.dumps('TODO: describe this preset.', ensure_ascii=True)}",
            "    params:",
            f"      color: {json.dumps('#33AAFF', ensure_ascii=True)}",
            "    tags:",
            "      - example",
            "",
        ]
    )


def _render_effect_python(
    *,
    class_name: str,
    effect_id: str,
    title: str,
    definition_type: str,
    overlay_mode: str | None,
) -> str:
    normalized_type = DefinitionType(str(definition_type).strip().lower())
    normalized_overlay_mode = None
    if normalized_type is DefinitionType.OVERLAY:
        if overlay_mode is None:
            raise ValueError("Overlay scaffolds must define overlay_mode as controlled or timed")
        normalized_overlay_mode = OverlayMode(str(overlay_mode).strip().lower())
    elif overlay_mode is not None:
        raise ValueError("overlay_mode is valid only for Overlay definitions")

    layer, playback_modes, duration_rule = _scaffold_lifecycle(
        normalized_type,
        normalized_overlay_mode,
    )
    import_names = (
        "BaseEffect, ColorModel, DefinitionType, EffectCapabilities, EffectDefinition, "
        "EffectParamDefinition, LayerId, LayerRule, OverlayMode, PlaybackMode, RenderContext"
    )
    finite_definition = normalized_type is DefinitionType.EVENT or (
        normalized_type is DefinitionType.OVERLAY
        and normalized_overlay_mode is OverlayMode.TIMED
    )
    lines = [
        "from __future__ import annotations",
        "",
        f"from respeaker_led.core.effect_schema import {import_names}",
        "",
        "",
        f"class {class_name}(BaseEffect):",
        "    definition = EffectDefinition(",
        f'        id="{effect_id}",',
        f'        title="{title}",',
        '        description="TODO: describe this definition.",',
        f"        definition_type=DefinitionType.{normalized_type.name},",
    ]
    if normalized_overlay_mode is not None:
        lines.append(f"        overlay_mode=OverlayMode.{normalized_overlay_mode.name},")
    lines.extend(
        [
            "        parameter_schema={",
            '            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),',
            '            "brightness": EffectParamDefinition(name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0, unit="ratio"),',
            *(
                [
                    '            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=1000, minimum=1, unit="ms"),',
                ]
                if finite_definition
                else []
            ),
            "        },",
            (
                '        defaults={"color": "#33AAFF", "brightness": 1.0, "duration_ms": 1000},'
                if finite_definition
                else '        defaults={"color": "#33AAFF", "brightness": 1.0},'
            ),
            "        capabilities=EffectCapabilities(",
            f"            playback_modes={playback_modes},",
            "            restorable=True,",
            "        ),",
            "        layer_rules={",
            f"            LayerId.{layer}: LayerRule(",
            "                allowed=True,",
            f"                allowed_playback_modes={playback_modes},",
            f"                {duration_rule}=True,",
            "            ),",
            "        },",
            "        color_model=ColorModel.MONO,",
            "    )",
            "",
            "    def render(self, ctx: RenderContext) -> list[int | None]:",
            '        raw_color = str(ctx.params.get("color", "#33AAFF")).replace("#", "0x")',
            "        color = int(raw_color, 16)",
            "        return [color] * ctx.led_count",
            "",
        ]
    )
    return "\n".join(lines)


def _scaffold_lifecycle(
    definition_type: DefinitionType,
    overlay_mode: OverlayMode | None,
) -> tuple[str, str, str]:
    if definition_type is DefinitionType.STATE:
        return (
            "STATE_LAYER",
            "(PlaybackMode.LOOP, PlaybackMode.PERSISTENT)",
            "requires_indefinite_duration",
        )
    if definition_type is DefinitionType.EVENT:
        return ("EVENT_LAYER", "(PlaybackMode.SINGLE_RUN,)", "requires_finite_duration")
    if overlay_mode is OverlayMode.TIMED:
        return ("TEMP_OVERLAY_LAYER", "(PlaybackMode.SINGLE_RUN,)", "requires_finite_duration")
    return (
        "ONGOING_OVERLAY_LAYER",
        "(PlaybackMode.LOOP, PlaybackMode.PERSISTENT)",
        "requires_indefinite_duration",
    )


def _write_text_file(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


def _title_from_effect_id(effect_id: str) -> str:
    return " ".join(part.capitalize() for part in str(effect_id).split("_") if part)


def _class_name_from_effect_id(effect_id: str) -> str:
    return "".join(part.capitalize() for part in str(effect_id).split("_") if part) + "Effect"
