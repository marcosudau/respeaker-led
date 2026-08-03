from __future__ import annotations

import shutil
from pathlib import Path

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
from src.engine.effect_package_builder import build_effect_package, build_effect_set
from src.engine.effect_package_loader import LoadedEffectPackage, load_effect_package, load_effect_set

from .effect_set_sources import (
    DEFAULT_BUILD_CACHE_ROOT,
    DEFAULT_GENERATED_ROOT,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_PACKAGE_CACHE_ROOT,
    DEFAULT_PUBLISH_ROOT,
    DEFAULT_SOURCES_ROOT,
    EffectSetSource,
    EffectSourceSpec,
    discover_effect_sets,
    discover_effect_sources,
)


def build_effect_packages_for_set(
    effect_set: EffectSetSource,
    *,
    package_cache_root: Path = DEFAULT_PACKAGE_CACHE_ROOT,
) -> list[Path]:
    specs = discover_effect_sources(effect_set)
    set_cache_root = Path(package_cache_root) / effect_set.set_id
    if set_cache_root.exists():
        shutil.rmtree(set_cache_root)
    set_cache_root.mkdir(parents=True, exist_ok=True)

    built_paths: list[Path] = []
    for spec in specs:
        artifact = build_effect_package(
            spec.source_dir,
            set_cache_root / f"{spec.effect_id}.lefx",
        )
        loaded = load_effect_package(artifact.output_path)
        _verify_package_identity(loaded, spec)
        _smoke_render(loaded)
        built_paths.append(artifact.output_path)
    return built_paths


def build_all_effect_packages(
    *,
    sources_root: Path = DEFAULT_SOURCES_ROOT,
    package_cache_root: Path = DEFAULT_PACKAGE_CACHE_ROOT,
) -> dict[str, list[Path]]:
    result: dict[str, list[Path]] = {}
    for effect_set in discover_effect_sets(sources_root):
        result[effect_set.set_id] = build_effect_packages_for_set(
            effect_set,
            package_cache_root=package_cache_root,
        )
    return result


def build_effect_set_for_source(
    effect_set: EffectSetSource,
    *,
    package_cache_root: Path = DEFAULT_PACKAGE_CACHE_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    publish_root: Path | None = DEFAULT_PUBLISH_ROOT,
    work_root: Path = DEFAULT_GENERATED_ROOT,
) -> Path:
    specs = discover_effect_sources(effect_set)
    expected_by_id = {spec.effect_id: spec for spec in specs}

    package_dir = Path(package_cache_root) / effect_set.set_id
    if not package_dir.is_dir():
        raise FileNotFoundError(
            f"No package cache directory for set {effect_set.set_id!r}: {package_dir}"
        )
    package_paths = sorted(package_dir.glob("*.lefx"))
    found_ids = {package_path.stem for package_path in package_paths}
    expected_ids = set(expected_by_id)

    missing = expected_ids - found_ids
    if missing:
        raise ValueError(
            f"Set {effect_set.set_id!r} is missing prebuilt packages: {sorted(missing)}"
        )
    extra = found_ids - expected_ids
    if extra:
        raise ValueError(
            f"Set {effect_set.set_id!r} contains unexpected/stale packages: {sorted(extra)}"
        )

    for package_path in package_paths:
        loaded = load_effect_package(package_path)
        spec = expected_by_id.get(loaded.manifest.effect_id)
        if spec is None:
            raise ValueError(
                f"Package {package_path.name!r} contains unknown effect "
                f"{loaded.manifest.effect_id!r} for set {effect_set.set_id!r}"
            )
        _verify_package_identity(loaded, spec)

    work = Path(work_root) / effect_set.set_id
    if work.exists():
        shutil.rmtree(work)
    effects_root = work / "effects"
    effects_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(effect_set.manifest_path, work / "set.yaml")
    for package_path in package_paths:
        shutil.copy2(package_path, effects_root / package_path.name)

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    artifact = build_effect_set(work, output_root / f"{effect_set.set_id}.lefxset")

    loaded_set = load_effect_set(artifact.output_path)
    actual_ids = {effect.manifest.effect_id for effect in loaded_set.effects}
    if actual_ids != expected_ids:
        raise ValueError(
            f"Built set {effect_set.set_id!r} contains {sorted(actual_ids)}, "
            f"expected {sorted(expected_ids)}"
        )

    if publish_root is not None:
        publish_root = Path(publish_root)
        publish_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(artifact.output_path, publish_root / f"{effect_set.set_id}.lefxset")
    return artifact.output_path


def build_all_effect_sets(
    *,
    sources_root: Path = DEFAULT_SOURCES_ROOT,
    package_cache_root: Path = DEFAULT_PACKAGE_CACHE_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    publish_root: Path | None = DEFAULT_PUBLISH_ROOT,
    work_root: Path = DEFAULT_GENERATED_ROOT,
) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for effect_set in discover_effect_sets(sources_root):
        result[effect_set.set_id] = build_effect_set_for_source(
            effect_set,
            package_cache_root=package_cache_root,
            output_root=output_root,
            publish_root=publish_root,
            work_root=work_root,
        )
    return result


def cleanup_effect_build_cache(
    cache_root: Path = DEFAULT_BUILD_CACHE_ROOT,
) -> None:
    if cache_root.exists():
        shutil.rmtree(cache_root)


def _verify_package_identity(loaded: LoadedEffectPackage, spec: EffectSourceSpec) -> None:
    if loaded.manifest.source_id != spec.source_id:
        raise ValueError(
            f"Package {loaded.origin_path!r} has source_id {loaded.manifest.source_id!r}, "
            f"expected {spec.source_id!r}"
        )
    if loaded.manifest.effect_id != spec.effect_id:
        raise ValueError(
            f"Package {loaded.origin_path!r} has effect_id {loaded.manifest.effect_id!r}, "
            f"expected {spec.effect_id!r}"
        )
    if loaded.manifest.package_id != spec.package_id:
        raise ValueError(
            f"Package {loaded.origin_path!r} has package_id {loaded.manifest.package_id!r}, "
            f"expected {spec.package_id!r}"
        )


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


__all__ = [
    "build_all_effect_packages",
    "build_all_effect_sets",
    "build_effect_packages_for_set",
    "build_effect_set_for_source",
    "cleanup_effect_build_cache",
]
