from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from src.core.effect_schema import BaseEffect, DefinitionType
from src.engine.effect_package_builder import _load_effect_class
from src.engine.effect_package_schema import load_source_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = PROJECT_ROOT / "tools" / "effect_building"
DEFAULT_BUILD_ROOT = Path(
    os.environ.get("LED_CONTROLLER_EFFECT_BUILD_ROOT", TOOLS_ROOT / "build")
).expanduser().resolve()
DEFAULT_BUILD_CACHE_ROOT = DEFAULT_BUILD_ROOT / ".cache"
DEFAULT_SOURCES_ROOT = TOOLS_ROOT / "sources"
DEFAULT_PACKAGE_CACHE_ROOT = DEFAULT_BUILD_CACHE_ROOT / "build_lefx"
DEFAULT_GENERATED_ROOT = DEFAULT_BUILD_CACHE_ROOT / "generated"
DEFAULT_OUTPUT_ROOT = DEFAULT_BUILD_ROOT / "output"
DEFAULT_PUBLISH_ROOT = DEFAULT_BUILD_ROOT / "published"

_ALLOWED_SET_MANIFEST_KEYS = frozenset(
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
    }
)
_TYPE_DIRS = ("states", "overlays", "events")
_TYPE_DIR_BY_DEFINITION_TYPE = {
    DefinitionType.STATE: "states",
    DefinitionType.OVERLAY: "overlays",
    DefinitionType.EVENT: "events",
}


@dataclass(frozen=True)
class EffectSetSource:
    set_id: str
    source_id: str
    title: str
    version: int
    min_service_version: str
    source_dir: Path
    manifest_path: Path
    description: str | None
    tags: tuple[str, ...]
    author: str | None
    vendor: str | None


@dataclass(frozen=True)
class EffectSourceSpec:
    set_id: str
    source_id: str
    effect_id: str
    package_id: str
    class_name: str
    effect_class: type[BaseEffect]
    source_dir: Path


def discover_effect_sets(
    sources_root: Path = DEFAULT_SOURCES_ROOT,
) -> list[EffectSetSource]:
    sources_root = Path(sources_root).resolve()
    if not sources_root.is_dir():
        raise FileNotFoundError(f"Effect sources root does not exist: {sources_root}")

    discovered: list[EffectSetSource] = []
    seen_set_ids: set[str] = set()
    seen_source_ids: set[str] = set()

    for manifest_path in sorted(sources_root.glob("*/set.yaml")):
        if not manifest_path.is_file():
            continue
        source_dir = manifest_path.parent
        metadata = load_source_manifest(source_dir, "set")
        _reject_unknown_keys(metadata, _ALLOWED_SET_MANIFEST_KEYS, "effect set manifest")

        set_id = str(metadata.get("set_id", "")).strip()
        source_id = str(metadata.get("source_id", "")).strip()
        if not set_id:
            raise ValueError(f"Effect set manifest {manifest_path} must define set_id")
        if not source_id:
            raise ValueError(f"Effect set manifest {manifest_path} must define source_id")
        if set_id in seen_set_ids:
            raise ValueError(f"Duplicate set_id detected: {set_id!r}")
        if source_id in seen_source_ids:
            raise ValueError(f"Duplicate source_id detected: {source_id!r}")
        if source_dir.name != set_id:
            raise ValueError(
                f"Set directory {source_dir.name!r} must match set_id {set_id!r} "
                f"(manifest: {manifest_path})"
            )
        seen_set_ids.add(set_id)
        seen_source_ids.add(source_id)

        tags = metadata.get("tags", [])
        if not isinstance(tags, list):
            raise ValueError(f"Effect set manifest {manifest_path} must define tags as a list")
        discovered.append(
            EffectSetSource(
                set_id=set_id,
                source_id=source_id,
                title=str(metadata.get("title", set_id)).strip(),
                version=int(metadata.get("version", 1)),
                min_service_version=str(metadata.get("min_service_version", "1.0.0")).strip(),
                source_dir=source_dir,
                manifest_path=manifest_path,
                description=(
                    None if metadata.get("description") is None else str(metadata["description"])
                ),
                tags=tuple(str(item) for item in tags),
                author=None if metadata.get("author") is None else str(metadata["author"]),
                vendor=None if metadata.get("vendor") is None else str(metadata["vendor"]),
            )
        )

    if not discovered:
        raise ValueError(
            f"No effect sets discovered under {sources_root}; "
            f"expected at least one sources/*/set.yaml manifest"
        )

    _reject_orphaned_effect_sources(sources_root, {item.source_dir for item in discovered})
    return discovered


def discover_effect_sources(
    effect_set: EffectSetSource,
) -> list[EffectSourceSpec]:
    root = effect_set.source_dir.resolve()
    specs: list[EffectSourceSpec] = []
    seen_ids: set[str] = set()

    for manifest_path in sorted(root.rglob("effect.yaml")):
        relative = manifest_path.relative_to(root)
        if (
            len(relative.parts) != 3
            or relative.parts[2] != "effect.yaml"
            or relative.parts[0] not in _TYPE_DIRS
        ):
            raise ValueError(
                f"Effect source {manifest_path} must live exactly under "
                f"sources/<set-id>/<states|overlays|events>/<effect-id>/effect.yaml"
            )
        type_dir_name = relative.parts[0]
        source_dir = manifest_path.parent
        metadata = load_source_manifest(source_dir, "effect")

        source_id = str(metadata.get("source_id", "")).strip()
        if source_id != effect_set.source_id:
            raise ValueError(
                f"Effect source {source_dir.name!r} uses source_id {source_id!r}, "
                f"expected {effect_set.source_id!r}"
            )

        entry_file = source_dir / str(metadata.get("entry_file", "effect.py"))
        if not entry_file.exists():
            raise FileNotFoundError(f"Effect source is missing entry file: {entry_file}")
        effect_class = _load_effect_class(
            source_dir,
            entry_file,
            None if metadata.get("entry_class") is None else str(metadata["entry_class"]),
        )
        definition = effect_class.get_definition()
        if definition.definition_type is None:
            raise ValueError(
                f"Effect {definition.id!r} in set {effect_set.set_id!r} must declare definition_type"
            )

        expected_type_dir = _TYPE_DIR_BY_DEFINITION_TYPE[definition.definition_type]
        if type_dir_name != expected_type_dir:
            raise ValueError(
                f"Effect {definition.id!r} belongs under {expected_type_dir!r}, "
                f"not {type_dir_name!r}"
            )
        if source_dir.name != definition.id:
            raise ValueError(
                f"Effect source folder {source_dir.name!r} must match id {definition.id!r}"
            )

        expected_package_id = f"{effect_set.source_id}.{definition.id}"
        package_id = str(metadata.get("package_id", expected_package_id)).strip()
        if package_id != expected_package_id:
            raise ValueError(
                f"Effect {definition.id!r} must use package_id {expected_package_id!r}, "
                f"got {package_id!r}"
            )
        if definition.id in seen_ids:
            raise ValueError(
                f"Duplicate effect id within set {effect_set.set_id!r}: {definition.id!r}"
            )
        seen_ids.add(definition.id)
        specs.append(
            EffectSourceSpec(
                set_id=effect_set.set_id,
                source_id=effect_set.source_id,
                effect_id=definition.id,
                package_id=package_id,
                class_name=effect_class.__name__,
                effect_class=effect_class,
                source_dir=source_dir,
            )
        )

    return sorted(specs, key=lambda item: item.effect_id)


def _reject_orphaned_effect_sources(
    sources_root: Path,
    set_roots: set[Path],
) -> None:
    for manifest_path in sorted(sources_root.rglob("effect.yaml")):
        if any(manifest_path.is_relative_to(set_root) for set_root in set_roots):
            continue
        raise ValueError(
            f"Orphaned/legacy effect source outside any discovered set root: {manifest_path}"
        )


def _reject_unknown_keys(
    payload: dict,
    allowed: frozenset[str],
    label: str,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"{label} contains unknown keys: {', '.join(unknown)}")


__all__ = [
    "DEFAULT_BUILD_CACHE_ROOT",
    "DEFAULT_BUILD_ROOT",
    "DEFAULT_GENERATED_ROOT",
    "DEFAULT_OUTPUT_ROOT",
    "DEFAULT_PACKAGE_CACHE_ROOT",
    "DEFAULT_PUBLISH_ROOT",
    "DEFAULT_SOURCES_ROOT",
    "EffectSetSource",
    "EffectSourceSpec",
    "discover_effect_sets",
    "discover_effect_sources",
]
