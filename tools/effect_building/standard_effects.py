from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.effect_schema import (
    BaseEffect,
    DefinitionType,
    EffectDefinition,
    EffectInvocation,
    LayerId,
    OverlayMode,
    PlaybackMode,
    RenderContext,
)
from src.engine.effect_package_builder import (
    _load_effect_class,
    build_effect_package,
    build_effect_set,
)
from src.engine.effect_package_loader import LoadedEffectPackage, load_effect_package, load_effect_set
from src.engine.effect_package_schema import load_source_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = PROJECT_ROOT / "tools" / "effect_building"
DEFAULT_SOURCE_ID = "default-effects"
DEFAULT_BUILD_ROOT = Path(
    os.environ.get("LED_CONTROLLER_EFFECT_BUILD_ROOT", TOOLS_ROOT / "build")
).expanduser().resolve()
DEFAULT_BUILD_CACHE_ROOT = DEFAULT_BUILD_ROOT / ".cache"
DEFAULT_SOURCES_ROOT = TOOLS_ROOT / "sources"
DEFAULT_LEFX_ROOT = DEFAULT_BUILD_CACHE_ROOT / "build_lefx" / DEFAULT_SOURCE_ID
DEFAULT_LEFXSET_ROOT = DEFAULT_BUILD_ROOT / "output"
DEFAULT_PUBLISH_COPY = DEFAULT_BUILD_ROOT / "published" / f"{DEFAULT_SOURCE_ID}.lefxset"
DEFAULT_SET_WORK_ROOT = DEFAULT_BUILD_CACHE_ROOT / "generated" / f"{DEFAULT_SOURCE_ID}_set"

@dataclass(frozen=True)
class EffectSourceSpec:
    effect_id: str
    class_name: str
    effect_class: type[BaseEffect]
    source_dir: Path

    @property
    def package_id(self) -> str:
        return f"{DEFAULT_SOURCE_ID}.{self.effect_id}"

def discover_standard_effects(source_root: Path = DEFAULT_SOURCES_ROOT) -> list[EffectSourceSpec]:
    source_root = Path(source_root).resolve()
    specs: list[EffectSourceSpec] = []
    seen_ids: set[str] = set()
    for manifest_path in sorted(source_root.rglob("effect.yaml")):
        relative = manifest_path.relative_to(source_root)
        if len(relative.parts) != 3 or relative.name != "effect.yaml":
            raise ValueError(
                "Standard effect sources must use "
                "sources/<states|overlays|events>/<id>/effect.yaml"
            )
        source_dir = manifest_path.parent
        metadata = load_source_manifest(source_dir, "effect")
        if metadata.get("source_id") != DEFAULT_SOURCE_ID:
            raise ValueError(
                f"Standard effect {source_dir.name!r} must use source_id {DEFAULT_SOURCE_ID!r}"
            )
        if metadata.get("entry_file", "effect.py") != "effect.py":
            raise ValueError(f"Standard effect {source_dir.name!r} must use entry_file 'effect.py'")
        if metadata.get("entry_class") != "Effect":
            raise ValueError(f"Standard effect {source_dir.name!r} must use entry_class 'Effect'")
        entry_file = source_dir / str(metadata.get("entry_file", "effect.py"))
        effect_class = _load_effect_class(
            source_dir,
            entry_file,
            None if metadata.get("entry_class") is None else str(metadata["entry_class"]),
        )
        definition = effect_class.get_definition()
        if definition.definition_type is None:
            raise ValueError(f"Standard effect {definition.id!r} must declare definition_type")
        expected_type_dir = f"{definition.definition_type.value}s"
        if source_dir.parent.name != expected_type_dir:
            raise ValueError(
                f"Standard effect {definition.id!r} belongs under {expected_type_dir!r}, "
                f"not {source_dir.parent.name!r}"
            )
        if source_dir.name != definition.id:
            raise ValueError(
                f"Standard effect folder {source_dir.name!r} must match id {definition.id!r}"
            )
        expected_package_id = f"{DEFAULT_SOURCE_ID}.{definition.id}"
        if metadata.get("package_id") != expected_package_id:
            raise ValueError(
                f"Standard effect {definition.id!r} must use package_id {expected_package_id!r}"
            )
        if definition.id in seen_ids:
            raise ValueError(f"Duplicate standard effect id: {definition.id!r}")
        seen_ids.add(definition.id)
        specs.append(
            EffectSourceSpec(
                effect_id=definition.id,
                class_name=effect_class.__name__,
                effect_class=effect_class,
                source_dir=source_dir,
            )
        )
    return sorted(specs, key=lambda item: item.effect_id)


def generate_standard_effect_sources(source_root: Path = DEFAULT_SOURCES_ROOT) -> list[Path]:
    source_root = Path(source_root).resolve()
    authoritative_root = DEFAULT_SOURCES_ROOT.resolve()
    if source_root == authoritative_root:
        return [spec.source_dir for spec in discover_standard_effects(authoritative_root)]
    if source_root.exists():
        shutil.rmtree(source_root)
    shutil.copytree(authoritative_root, source_root)
    return [spec.source_dir for spec in discover_standard_effects(source_root)]


def build_standard_effect_packages(source_root: Path = DEFAULT_SOURCES_ROOT, output_root: Path = DEFAULT_LEFX_ROOT) -> list[Path]:
    generate_standard_effect_sources(source_root)
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    built_paths: list[Path] = []
    for spec in discover_standard_effects(source_root):
        artifact = build_effect_package(spec.source_dir, output_root / f"{spec.effect_id}.lefx")
        loaded = load_effect_package(artifact.output_path)
        _smoke_render(loaded)
        built_paths.append(artifact.output_path)
    return built_paths


def build_standard_effect_set(
    package_root: Path = DEFAULT_LEFX_ROOT,
    output_root: Path = DEFAULT_LEFXSET_ROOT,
    publish_copy: Path | None = DEFAULT_PUBLISH_COPY,
    work_root: Path = DEFAULT_SET_WORK_ROOT,
) -> Path:
    package_paths = sorted(package_root.glob("*.lefx"))
    if not package_paths:
        raise FileNotFoundError(f"No .lefx packages found under {package_root}")

    if work_root.exists():
        shutil.rmtree(work_root)
    try:
        effects_root = work_root / "effects"
        effects_root.mkdir(parents=True, exist_ok=True)
        for package_path in package_paths:
            shutil.copy2(package_path, effects_root / package_path.name)

        (work_root / "set.yaml").write_text(
            _dump_yaml(
                {
                    "set_id": DEFAULT_SOURCE_ID,
                    "source_id": DEFAULT_SOURCE_ID,
                    "title": "Default Effects",
                    "version": 1,
                    "min_service_version": "1.0.0",
                    "effects": [package_path.name for package_path in package_paths],
                }
            ),
            encoding="utf-8",
        )

        output_root.mkdir(parents=True, exist_ok=True)
        artifact = build_effect_set(work_root, output_root / f"{DEFAULT_SOURCE_ID}.lefxset")
        loaded = load_effect_set(artifact.output_path)
        if len(loaded.effects) != len(package_paths):
            raise ValueError("Built effect set does not contain every packaged standard effect")

        if publish_copy is not None:
            publish_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(artifact.output_path, publish_copy)
        return artifact.output_path
    finally:
        if work_root.exists():
            shutil.rmtree(work_root)


def cleanup_standard_build_cache(cache_root: Path = DEFAULT_BUILD_CACHE_ROOT) -> None:
    if cache_root.exists():
        shutil.rmtree(cache_root)


def build_default_effects() -> dict[str, Any]:
    packages = build_standard_effect_packages()
    effect_set = build_standard_effect_set()
    return {
        "source_root": str(DEFAULT_SOURCES_ROOT),
        "package_root": str(DEFAULT_LEFX_ROOT),
        "effect_set": str(effect_set),
        "publish_copy": str(DEFAULT_PUBLISH_COPY),
        "source_count": len(discover_standard_effects()),
        "package_count": len(packages),
    }


def _smoke_render(loaded: LoadedEffectPackage) -> None:
    definition = loaded.effect_class.get_definition()
    layer_id, playback_mode, requested_duration_ms = _smoke_render_setup(definition)
    frame = loaded.effect_class().render(
        RenderContext(
            now=0.5,
            led_count=12,
            layer_id=layer_id,
            definition=definition,
            invocation=EffectInvocation(
                invocation_id=f"smoke::{definition.id}",
                effect_id=definition.id,
                target_layer=layer_id,
                playback_mode=playback_mode,
                created_at=0.0,
                requested_duration_ms=requested_duration_ms,
            ),
            params=dict(definition.defaults),
            inputs={},
        )
    )
    if len(frame) != 12:
        raise ValueError(f"Effect {definition.id!r} rendered {len(frame)} LEDs instead of 12")


def _smoke_render_setup(definition: EffectDefinition) -> tuple[LayerId, PlaybackMode | None, int | None]:
    if definition.definition_type is DefinitionType.STATE:
        layer_id = (
            LayerId.STATE_LAYER
            if LayerId.STATE_LAYER in definition.layer_rules
            else LayerId.BACKGROUND_STATE_LAYER
        )
    elif definition.definition_type is DefinitionType.OVERLAY:
        layer_id = (
            LayerId.TEMP_OVERLAY_LAYER
            if definition.overlay_mode is OverlayMode.TIMED
            else LayerId.ONGOING_OVERLAY_LAYER
        )
    elif definition.definition_type is DefinitionType.EVENT:
        layer_id = LayerId.EVENT_LAYER
    else:
        raise ValueError(f"Effect {definition.id!r} does not declare a definition type")
    rule = definition.layer_rules[layer_id]
    playback_modes = rule.allowed_playback_modes or definition.capabilities.playback_modes or (PlaybackMode.SINGLE_RUN,)
    requested_duration_ms = None
    if rule.requires_finite_duration:
        requested_duration_ms = int(
            definition.defaults.get("duration_ms", definition.defaults.get("total_ms", 1000)) or 1000
        )
    return layer_id, playback_modes[0], requested_duration_ms


def _dump_yaml(payload: dict[str, Any]) -> str:
    lines: list[str] = []

    def emit(value: Any, indent: int, key: str | None = None) -> None:
        prefix = " " * indent
        if isinstance(value, dict):
            if key is not None:
                lines.append(f"{prefix}{key}:")
            next_indent = indent + (2 if key is not None else 0)
            for nested_key, nested_value in value.items():
                emit(nested_value, next_indent, str(nested_key))
            return
        if isinstance(value, (list, tuple)):
            if key is not None:
                lines.append(f"{prefix}{key}:")
            list_indent = prefix if key is None else " " * (indent + 2)
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{list_indent}-")
                    for nested_key, nested_value in item.items():
                        emit(nested_value, indent + 4, str(nested_key))
                    continue
                lines.append(f"{list_indent}- {_yaml_scalar(item)}")
            return
        lines.append(f"{prefix}{key}: {_yaml_scalar(value)}")

    for top_key, top_value in payload.items():
        emit(top_value, 0, str(top_key))
    return "\n".join(lines) + "\n"


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if any(char in text for char in "#:[]{}\"'") or text.strip() != text:
        return json.dumps(text, ensure_ascii=True)
    return text


__all__ = [
    "DEFAULT_LEFX_ROOT",
    "DEFAULT_LEFXSET_ROOT",
    "DEFAULT_BUILD_CACHE_ROOT",
    "DEFAULT_BUILD_ROOT",
    "DEFAULT_PUBLISH_COPY",
    "DEFAULT_SOURCE_ID",
    "DEFAULT_SOURCES_ROOT",
    "build_default_effects",
    "build_standard_effect_packages",
    "build_standard_effect_set",
    "cleanup_standard_build_cache",
    "discover_standard_effects",
    "generate_standard_effect_sources",
]
