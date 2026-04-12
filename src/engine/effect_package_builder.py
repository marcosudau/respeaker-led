from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

from ..core.effect_schema import BaseEffect
from .effect_command_registry import EffectCommandDefinition, parse_command_definitions
from .effect_package_loader import load_effect_package
from .effect_package_schema import (
    EffectPackageManifest,
    EffectSetManifest,
    load_optional_source_manifest,
    load_source_manifest,
    serialize_effect_definition,
)
from .effect_preset_registry import EffectPresetDefinition, parse_effect_preset_definitions


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
            "command_count": len(built["commands"]),
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
            "command_count": built["command_count"],
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
    layer: str = "MAIN_LAYER",
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
        layer=layer,
    )
    effect_py = _render_effect_python(
        class_name=normalized_class_name,
        effect_id=effect_id,
        title=normalized_title,
        layer=layer,
    )
    preset_text = _render_effect_presets_template(title=normalized_title, layer=layer)
    command_text = _render_commands_template(layer=layer)

    created_files = [
        _write_text_file(metadata_path, metadata_text),
        _write_text_file(target / "effect-presets.yaml", preset_text),
        _write_text_file(target / "commands.json", command_text),
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
                layer=str(item.get("layer", "MAIN_LAYER")),
                format_name=str(item.get("format", "yaml")),
                force=force,
            )
        )
    return results


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

    presets_payload = load_optional_source_manifest(source_dir, "effect-presets")
    presets = (
        []
        if presets_payload is None
        else parse_effect_preset_definitions(source_id, definition, presets_payload)
    )

    commands_payload = _load_optional_commands_payload(source_dir)
    commands = (
        []
        if commands_payload is None
        else parse_command_definitions(
            source_id,
            commands_payload,
            presets=presets,
            default_effect_id=definition.id,
            source_effect_ids={manifest.qualified_effect_id},
        )
    )

    files = _collect_payload_files(source_dir)
    archive_bytes = _build_effect_archive(manifest, files, presets=presets, commands_payload=commands_payload)
    return {
        "bytes": archive_bytes,
        "manifest": manifest,
        "presets": presets,
        "commands": commands,
        "warnings": [],
    }


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
    command_names: set[str] = set()
    preset_count = 0
    command_count = 0

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
            command_count += _track_command_names(command_names, built["commands"], source_id=source_id)
            continue

        loaded = load_effect_package(item)
        if loaded.manifest.source_id != source_id:
            raise ValueError(
                f"Effect package {item.name!r} has source_id {loaded.manifest.source_id!r}, expected {source_id!r}"
            )
        nested_packages.append((f"effects/{item.name}", item.read_bytes(), loaded.manifest))
        preset_count += _track_preset_ids(preset_ids, list(loaded.presets))
        command_count += _track_command_names(command_names, list(loaded.commands), source_id=source_id)

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
        command_namespace=None,
    )
    archive_bytes = _build_effect_set_archive(manifest, nested_packages)
    return {
        "bytes": archive_bytes,
        "manifest": manifest,
        "warnings": warnings,
        "preset_count": preset_count,
        "command_count": command_count,
    }


def _track_preset_ids(seen: set[str], presets: list[EffectPresetDefinition]) -> int:
    for preset in presets:
        if preset.preset_id in seen:
            raise ValueError(f"Duplicate preset id detected within source: {preset.preset_id!r}")
        seen.add(preset.preset_id)
    return len(presets)


def _track_command_names(seen: set[str], commands: list[EffectCommandDefinition], *, source_id: str) -> int:
    for command in commands:
        if command.source_id != source_id:
            raise ValueError(
                f"Command {command.command_name!r} belongs to source {command.source_id!r}, expected {source_id!r}"
            )
        if command.command_name in seen:
            raise ValueError(f"Duplicate command name detected within source: {command.command_name!r}")
        seen.add(command.command_name)
    return len(commands)


def _resolve_effect_set_member(effects_root: Path, raw_name: str) -> Path:
    candidate = effects_root / raw_name
    if candidate.exists():
        return candidate
    lefx_candidate = effects_root / f"{raw_name}.lefx"
    if lefx_candidate.exists():
        return lefx_candidate
    raise FileNotFoundError(f"Effect set member could not be resolved: {raw_name}")


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
        raise ValueError(
            f"Source effect module {entry_file} must contain exactly one BaseEffect subclass when entry_class is omitted"
        )
    return discovered[0]


def _collect_payload_files(source_dir: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {"payload/__init__.py": b""}
    for path in sorted(source_dir.rglob("*")):
        if path.is_dir():
            continue
        if "__pycache__" in path.parts:
            continue
        if path.name in {"effect.json", "effect.yaml", "effect-presets.json", "effect-presets.yaml", "commands.json"}:
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


def _build_effect_archive(
    manifest: EffectPackageManifest,
    files: dict[str, bytes],
    *,
    presets: list[EffectPresetDefinition],
    commands_payload: dict[str, Any] | None,
) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest_bytes = json.dumps(manifest.to_dict(), ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
        archive.writestr("manifest.json", manifest_bytes)
        hashes = {"manifest.json": hashlib.sha256(manifest_bytes).hexdigest()}

        if presets:
            preset_bytes = json.dumps(
                {"presets": {preset.preset_id: _serialize_preset_payload(preset) for preset in presets}},
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            ).encode("utf-8")
            archive.writestr("effect-presets.json", preset_bytes)
            hashes["effect-presets.json"] = hashlib.sha256(preset_bytes).hexdigest()

        if commands_payload is not None:
            command_bytes = json.dumps(commands_payload, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
            archive.writestr("commands.json", command_bytes)
            hashes["commands.json"] = hashlib.sha256(command_bytes).hexdigest()

        for name, content in files.items():
            archive.writestr(name, content)
            hashes[name] = hashlib.sha256(content).hexdigest()

        hash_bytes = json.dumps({"algorithm": "sha256", "files": hashes}, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
        archive.writestr("hashes.json", hash_bytes)
    return buffer.getvalue()


def _serialize_preset_payload(preset: EffectPresetDefinition) -> dict[str, Any]:
    payload = {
        "category": preset.category,
        "target_layer": preset.target_layer.value,
        "params": dict(preset.params),
        "enqueue": preset.enqueue,
        "replace_existing": preset.replace_existing,
        "tags": list(preset.tags),
    }
    if preset.title is not None:
        payload["title"] = preset.title
    if preset.description is not None:
        payload["description"] = preset.description
    if preset.duration_ms is not None:
        payload["duration_ms"] = preset.duration_ms
    if preset.priority is not None:
        payload["priority"] = preset.priority
    return payload


def _build_effect_set_archive(
    manifest: EffectSetManifest,
    nested_packages: list[tuple[str, bytes, EffectPackageManifest]],
) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest_bytes = json.dumps(manifest.to_dict(), ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
        archive.writestr("set-manifest.json", manifest_bytes)
        hashes = {"set-manifest.json": hashlib.sha256(manifest_bytes).hexdigest()}
        for file_name, payload, _ in nested_packages:
            archive.writestr(file_name, payload)
            hashes[file_name] = hashlib.sha256(payload).hexdigest()
        hash_bytes = json.dumps({"algorithm": "sha256", "files": hashes}, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
        archive.writestr("hashes.json", hash_bytes)
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
    layer: str,
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
                    "layer_hint": layer,
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
            f"# Suggested primary layer: {layer}",
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
            "  # - add prebuilt .lefx file names or transitional source directory names here",
            "",
        ]
    )


def _render_effect_presets_template(*, title: str, layer: str) -> str:
    category = _layer_to_preset_category(layer)
    preset_id = f"{category}_example"
    return "\n".join(
        [
            "# Optional embedded presets for this effect.",
            "# Preset ids must stay source-local and use the category prefix.",
            "presets:",
            f"  {preset_id}:",
            f"    title: {json.dumps(f'{title} Example', ensure_ascii=True)}",
            f"    description: {json.dumps('TODO: describe this preset.', ensure_ascii=True)}",
            f"    category: {category}",
            f"    target_layer: {layer}",
            "    params:",
            f"      color: {json.dumps('#33AAFF', ensure_ascii=True)}",
            "    tags:",
            f"      - {category}",
            "",
        ]
    )


def _render_commands_template(*, layer: str) -> str:
    category = _layer_to_preset_category(layer)
    preset_id = f"{category}_example"
    target_layer = _category_to_default_layer(category)
    example = {
        "commands": {
            f"{category}_example": {
                "kind": "event" if category == "event" else "state_toggle",
                "on": {
                    "preset": preset_id,
                },
            }
        }
    }
    if category != "event":
        example["commands"][f"{category}_example"]["off"] = {
            "action": "clear_layer",
            "target_layer": target_layer,
        }
    return json.dumps(example, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def _render_effect_python(*, class_name: str, effect_id: str, title: str, layer: str) -> str:
    return "\n".join(
        [
            "from __future__ import annotations",
            "",
            "from src.core.effect_schema import BaseEffect, EffectCapabilities, EffectDefinition, EffectParamDefinition, LayerId, LayerRule, PlaybackMode, RenderContext",
            "",
            "",
            f"class {class_name}(BaseEffect):",
            "    definition = EffectDefinition(",
            f'        id="{effect_id}",',
            f'        title="{title}",',
            '        description="TODO: describe this effect.",',
            "        parameter_schema={",
            '            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),',
            "        },",
            '        defaults={"color": "#33AAFF"},',
            "        capabilities=EffectCapabilities(",
            "            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),",
            "            restorable=True,",
            "        ),",
            "        layer_rules={",
            f"            LayerId.{layer}: LayerRule(",
            "                allowed=True,",
            "                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),",
            "            ),",
            "        },",
            "    )",
            "",
            "    def render(self, ctx: RenderContext) -> list[int | None]:",
            '        raw_color = str(ctx.params.get("color", "#33AAFF")).replace("#", "0x")',
            "        color = int(raw_color, 16)",
            "        return [color] * ctx.led_count",
            "",
        ]
    )


def _load_optional_commands_payload(source_dir: Path) -> dict[str, Any] | None:
    commands_path = source_dir / "commands.json"
    if not commands_path.exists():
        return None
    return json.loads(commands_path.read_text(encoding="utf-8"))


def _layer_to_preset_category(layer: str) -> str:
    normalized = str(layer).strip().upper()
    if normalized in {"BACKGROUND_STATE_LAYER", "STATE_LAYER"}:
        return "state"
    if normalized in {"TEMP_OVERLAY_LAYER", "ONGOING_OVERLAY_LAYER"}:
        return "overlay"
    if normalized == "EVENT_LAYER":
        return "event"
    return "effect"
def _category_to_default_layer(category: str) -> str:
    if category == "state":
        return "STATE_LAYER"
    if category == "overlay":
        return "ONGOING_OVERLAY_LAYER"
    if category == "event":
        return "EVENT_LAYER"
    return "MAIN_LAYER"


def _write_text_file(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


def _title_from_effect_id(effect_id: str) -> str:
    return " ".join(part.capitalize() for part in str(effect_id).split("_") if part)


def _class_name_from_effect_id(effect_id: str) -> str:
    return "".join(part.capitalize() for part in str(effect_id).split("_") if part) + "Effect"
