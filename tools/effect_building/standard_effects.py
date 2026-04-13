from __future__ import annotations

import importlib
import inspect
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.effect_schema import BaseEffect, EffectDefinition, EffectInvocation, LayerId, PlaybackMode, RenderContext
from src.engine.effect_package_builder import build_effect_package, build_effect_set
from src.engine.effect_package_loader import LoadedEffectPackage, load_effect_package, load_effect_set


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = PROJECT_ROOT / "tools" / "effect_building"
DEFAULT_SOURCE_ID = "default-effects"
DEFAULT_SOURCES_ROOT = TOOLS_ROOT / "sources" / DEFAULT_SOURCE_ID
DEFAULT_LEFX_ROOT = TOOLS_ROOT / "build_lefx" / DEFAULT_SOURCE_ID
DEFAULT_LEFXSET_ROOT = TOOLS_ROOT / "build_lefxset"
DEFAULT_PUBLISH_COPY = PROJECT_ROOT / "src" / "led_effects" / f"{DEFAULT_SOURCE_ID}.lefxset"
DEFAULT_SET_WORK_ROOT = TOOLS_ROOT / "_generated" / f"{DEFAULT_SOURCE_ID}_set"

_MODULE_BUNDLES = (
    (
        "tools.effect_building.effects.basic",
        PROJECT_ROOT / "tools" / "effect_building" / "effects" / "basic.py",
        (
            PROJECT_ROOT / "tools" / "effect_building" / "effects" / "common.py",
        ),
    ),
    (
        "tools.effect_building.effects.overlays",
        PROJECT_ROOT / "tools" / "effect_building" / "effects" / "overlays.py",
        (
            PROJECT_ROOT / "tools" / "effect_building" / "effects" / "basic.py",
            PROJECT_ROOT / "tools" / "effect_building" / "effects" / "common.py",
        ),
    ),
    (
        "tools.effect_building.effects.ring_effects",
        PROJECT_ROOT / "tools" / "effect_building" / "effects" / "ring_effects.py",
        (
            PROJECT_ROOT / "tools" / "effect_building" / "effects" / "common.py",
        ),
    ),
)

_CATEGORY_VARIANTS: dict[str, tuple[str, ...]] = {
    "state": ("idle", "focus", "ready", "rest"),
    "effect": ("main", "accent", "pulse", "cinema"),
    "overlay": ("assist", "tracking", "guide", "marker"),
    "event": ("alert", "notice", "success", "urgent"),
}

_THEMES: dict[str, dict[str, Any]] = {
    "idle": {"primary": "#4A7BFF", "secondary": "#9BC6FF", "accent": "#7FD1FF", "background": "#020814", "brightness": 0.45, "speed": 0.7, "level": 28.0, "duration_ms": 1400, "direction_deg": 90.0, "start_led": 0},
    "focus": {"primary": "#2ED3A8", "secondary": "#C4FFF0", "accent": "#5DFFC8", "background": "#03110D", "brightness": 0.72, "speed": 1.1, "level": 56.0, "duration_ms": 1800, "direction_deg": 180.0, "start_led": 2},
    "ready": {"primary": "#5BC0FF", "secondary": "#D9F2FF", "accent": "#89D6FF", "background": "#041018", "brightness": 0.66, "speed": 0.95, "level": 42.0, "duration_ms": 1600, "direction_deg": 120.0, "start_led": 1},
    "rest": {"primary": "#7AA4FF", "secondary": "#DCE7FF", "accent": "#B7C7FF", "background": "#05070C", "brightness": 0.38, "speed": 0.55, "level": 18.0, "duration_ms": 1200, "direction_deg": 300.0, "start_led": 5},
    "main": {"primary": "#55A8FF", "secondary": "#E0F2FF", "accent": "#FFB347", "background": "#03070C", "brightness": 0.8, "speed": 1.0, "level": 64.0, "duration_ms": 1200, "direction_deg": 60.0, "start_led": 0},
    "accent": {"primary": "#FFB347", "secondary": "#FFD7A1", "accent": "#FF7A59", "background": "#140804", "brightness": 0.9, "speed": 1.35, "level": 82.0, "duration_ms": 1100, "direction_deg": 240.0, "start_led": 3},
    "pulse": {"primary": "#33AAFF", "secondary": "#8EDBFF", "accent": "#42D392", "background": "#020A10", "brightness": 0.78, "speed": 1.2, "level": 74.0, "duration_ms": 1500, "direction_deg": 30.0, "start_led": 4},
    "cinema": {"primary": "#D9475C", "secondary": "#FFC4D2", "accent": "#FFCE73", "background": "#120206", "brightness": 0.88, "speed": 0.85, "level": 68.0, "duration_ms": 1700, "direction_deg": 200.0, "start_led": 6},
    "assist": {"primary": "#7FC9FF", "secondary": "#EAF8FF", "accent": "#B8EBFF", "background": "#000000", "brightness": 0.6, "speed": 0.8, "level": 34.0, "duration_ms": 2000, "direction_deg": 90.0, "start_led": 0},
    "tracking": {"primary": "#33FFAA", "secondary": "#D8FFF0", "accent": "#7DFFE0", "background": "#000000", "brightness": 0.85, "speed": 1.25, "level": 62.0, "duration_ms": 2200, "direction_deg": 150.0, "start_led": 1},
    "guide": {"primary": "#FFD166", "secondary": "#FFF0C2", "accent": "#FFF3D1", "background": "#090703", "brightness": 0.78, "speed": 0.9, "level": 48.0, "duration_ms": 2400, "direction_deg": 210.0, "start_led": 5},
    "marker": {"primary": "#FF8AAE", "secondary": "#FFD3E0", "accent": "#FFB7CB", "background": "#090205", "brightness": 0.74, "speed": 1.05, "level": 52.0, "duration_ms": 1800, "direction_deg": 300.0, "start_led": 7},
    "alert": {"primary": "#FF5A5A", "secondary": "#FFD0D0", "accent": "#FF9F1A", "background": "#120102", "brightness": 1.0, "speed": 1.35, "level": 100.0, "duration_ms": 900, "direction_deg": 0.0, "start_led": 0},
    "notice": {"primary": "#FFD166", "secondary": "#FFF0C2", "accent": "#FFB347", "background": "#120A02", "brightness": 0.9, "speed": 1.1, "level": 72.0, "duration_ms": 1000, "direction_deg": 180.0, "start_led": 2},
    "success": {"primary": "#42D392", "secondary": "#D7FFF0", "accent": "#7EF0B5", "background": "#02110A", "brightness": 0.88, "speed": 0.95, "level": 80.0, "duration_ms": 950, "direction_deg": 120.0, "start_led": 4},
    "urgent": {"primary": "#FF3B30", "secondary": "#FFDAD7", "accent": "#FF8C69", "background": "#170102", "brightness": 1.0, "speed": 1.6, "level": 100.0, "duration_ms": 700, "direction_deg": 270.0, "start_led": 6},
}


@dataclass(frozen=True)
class EffectSourceSpec:
    effect_id: str
    class_name: str
    effect_class: type[BaseEffect]
    module_file: Path
    dependency_files: tuple[Path, ...]

    @property
    def package_id(self) -> str:
        return f"{DEFAULT_SOURCE_ID}.{self.effect_id}"


@dataclass(frozen=True)
class PresetPlan:
    preset_id: str
    category: str
    target_layer: LayerId
    params: dict[str, Any]
    title: str
    description: str
    duration_ms: int | None = None
    priority: int | None = None
    enqueue: bool = False
    replace_existing: bool = True
    tags: tuple[str, ...] = ()


def discover_standard_effects() -> list[EffectSourceSpec]:
    specs: list[EffectSourceSpec] = []
    for module_name, module_file, dependency_files in _MODULE_BUNDLES:
        module = importlib.import_module(module_name)
        for value in module.__dict__.values():
            if not inspect.isclass(value):
                continue
            if value is BaseEffect or not issubclass(value, BaseEffect) or inspect.isabstract(value):
                continue
            if value.__module__ != module.__name__:
                continue
            definition = value.get_definition()
            specs.append(
                EffectSourceSpec(
                    effect_id=definition.id,
                    class_name=value.__name__,
                    effect_class=value,
                    module_file=module_file,
                    dependency_files=dependency_files,
                )
            )
    return sorted(specs, key=lambda item: item.effect_id)


def generate_standard_effect_sources(source_root: Path = DEFAULT_SOURCES_ROOT) -> list[Path]:
    if source_root.exists():
        shutil.rmtree(source_root)
    source_root.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    for spec in discover_standard_effects():
        target_dir = source_root / spec.effect_id
        _write_effect_source(spec, target_dir)
        created.append(target_dir)
    return created


def build_standard_effect_packages(source_root: Path = DEFAULT_SOURCES_ROOT, output_root: Path = DEFAULT_LEFX_ROOT) -> list[Path]:
    generate_standard_effect_sources(source_root)
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    built_paths: list[Path] = []
    for spec in discover_standard_effects():
        artifact = build_effect_package(source_root / spec.effect_id, output_root / f"{spec.effect_id}.lefx")
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


def _write_effect_source(spec: EffectSourceSpec, target_dir: Path) -> None:
    preset_plans = _build_preset_plans(spec)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "effect.yaml").write_text(
        _dump_yaml(
            {
                "package_id": spec.package_id,
                "source_id": DEFAULT_SOURCE_ID,
                "entry_file": "effect.py",
                "entry_class": spec.class_name,
                "min_service_version": "1.0.0",
            }
        ),
        encoding="utf-8",
    )
    (target_dir / "effect.py").write_text(_transformed_module_text(spec.module_file), encoding="utf-8")
    for dependency_file in spec.dependency_files:
        (target_dir / dependency_file.name).write_text(_transformed_module_text(dependency_file), encoding="utf-8")
    (target_dir / "presets.yaml").write_text(_dump_yaml({"presets": _serialize_presets(preset_plans)}), encoding="utf-8")
    (target_dir / "commands.json").write_text(
        json.dumps({"commands": _build_commands_payload(preset_plans)}, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (target_dir / "assets").mkdir(exist_ok=True)
    (target_dir / "extra").mkdir(exist_ok=True)
    (target_dir / "extra" / "__init__.py").write_text("from __future__ import annotations\n", encoding="utf-8")


def _build_preset_plans(spec: EffectSourceSpec) -> list[PresetPlan]:
    definition = spec.effect_class.get_definition()
    supported = _supported_category_layers(definition)
    if not supported:
        raise ValueError(f"Effect {spec.effect_id!r} does not expose any supported preset categories")

    plans: list[PresetPlan] = []
    used_counts = {category: 0 for category in _CATEGORY_VARIANTS}

    def append_variants(category: str, count: int) -> None:
        if category not in supported or count <= 0:
            return
        variants = _CATEGORY_VARIANTS[category]
        start = used_counts[category]
        for variant in variants[start : start + count]:
            plans.append(_make_preset_plan(definition, category, supported[category], variant))
            used_counts[category] += 1

    if "state" in supported:
        append_variants("state", 2)
    for category in ("effect", "overlay", "event"):
        if len(plans) >= 4:
            break
        append_variants(category, min(2, 4 - len(plans)))
    if len(plans) < 4:
        fallback = "state" if "state" in supported else next(iter(supported))
        append_variants(fallback, 4 - len(plans))
    return plans


def _supported_category_layers(definition: EffectDefinition) -> dict[str, LayerId]:
    supported: dict[str, LayerId] = {}
    if _allows_layer(definition, LayerId.STATE_LAYER):
        supported["state"] = LayerId.STATE_LAYER
    elif _allows_layer(definition, LayerId.BACKGROUND_STATE_LAYER):
        supported["state"] = LayerId.BACKGROUND_STATE_LAYER
    if _allows_layer(definition, LayerId.MAIN_LAYER):
        supported["effect"] = LayerId.MAIN_LAYER
    if _allows_layer(definition, LayerId.ONGOING_OVERLAY_LAYER):
        supported["overlay"] = LayerId.ONGOING_OVERLAY_LAYER
    elif _allows_layer(definition, LayerId.TEMP_OVERLAY_LAYER):
        supported["overlay"] = LayerId.TEMP_OVERLAY_LAYER
    if _allows_layer(definition, LayerId.EVENT_LAYER):
        supported["event"] = LayerId.EVENT_LAYER
    return supported


def _allows_layer(definition: EffectDefinition, layer_id: LayerId) -> bool:
    rule = definition.layer_rules.get(layer_id)
    return rule is not None and rule.allowed


def _make_preset_plan(definition: EffectDefinition, category: str, target_layer: LayerId, variant: str) -> PresetPlan:
    theme = _THEMES[variant]
    params = _build_params(definition, category, variant, theme)
    duration_ms = int(theme["duration_ms"]) if category == "event" or target_layer is LayerId.TEMP_OVERLAY_LAYER else None
    return PresetPlan(
        preset_id=f"{category}_{definition.id}_{variant}",
        category=category,
        target_layer=target_layer,
        params=params,
        title=f"{definition.title} {variant.replace('_', ' ').title()}",
        description=f"Auto-generated {category} preset for {definition.id} ({variant}).",
        duration_ms=duration_ms,
        priority=700 if category == "event" else None,
        enqueue=category == "event",
        replace_existing=True,
        tags=(category, variant, definition.id),
    )


def _build_params(definition: EffectDefinition, category: str, variant: str, theme: dict[str, Any]) -> dict[str, Any]:
    available = {_normalized_param_name(name) for name in definition.parameter_schema}
    params: dict[str, Any] = {}
    mapping: dict[str, Any] = {
        "color": theme["primary"],
        "color_a": theme["primary"],
        "color_b": theme["secondary"],
        "center_color": theme["secondary"],
        "side_color": theme["accent"],
        "marker_color": theme["secondary"],
        "background_color": theme["background"],
        "brightness": theme["brightness"],
        "speed": theme["speed"],
        "value": theme["level"],
        "fill_level": theme["level"],
        "progress_value": theme["level"],
        "direction": theme["direction_deg"],
        "direction_deg": theme["direction_deg"],
        "duration_ms": int(theme["duration_ms"]),
        "total_ms": max(int(theme["duration_ms"]) * 2, 1000),
        "pause_ms": 120,
        "segment_length": 3 if category == "event" else 4,
        "trail_length": 5,
        "sparkle_count": 4,
        "point_size": 2,
        "start_led": int(theme["start_led"]),
        "position": int(theme["start_led"]),
        "position_a": int(theme["start_led"]),
        "position_b": (int(theme["start_led"]) + 6) % 12,
        "target_led": int(theme["start_led"]),
        "reverse": variant in {"accent", "tracking", "urgent", "marker"},
        "duty_cycle": 0.45 if variant in {"idle", "assist"} else 0.55,
    }
    if "min_brightness" in available:
        mapping["min_brightness"] = round(min(float(theme["brightness"]) * 0.25, 0.25), 2)
    if "gradient_colors" in available:
        mapping["gradient_colors"] = [theme["primary"], theme["accent"]]
    if "pattern" in available:
        mapping["pattern"] = {
            "idle": "single",
            "focus": "double",
            "ready": "continuous",
            "rest": "single",
            "main": "single",
            "accent": "double",
            "pulse": "triple",
            "cinema": "continuous",
            "assist": "single",
            "tracking": "double",
            "guide": "triple",
            "marker": "single",
            "alert": "single",
            "notice": "double",
            "success": "single",
            "urgent": "triple",
        }[variant]
    for key, value in mapping.items():
        if key in available:
            params[key] = value
    return params


def _normalized_param_name(name: str) -> str:
    if name == "base_color":
        return "background_color"
    if name == "direction_deg":
        return "direction"
    return name


def _serialize_presets(plans: list[PresetPlan]) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {}
    for plan in plans:
        item: dict[str, Any] = {
            "title": plan.title,
            "description": plan.description,
            "category": plan.category,
            "target_layer": plan.target_layer.value,
            "params": dict(plan.params),
            "replace_existing": plan.replace_existing,
            "tags": list(plan.tags),
        }
        if plan.duration_ms is not None:
            item["duration_ms"] = plan.duration_ms
        if plan.priority is not None:
            item["priority"] = plan.priority
        if plan.enqueue:
            item["enqueue"] = True
        payload[plan.preset_id] = item
    return payload


def _build_commands_payload(plans: list[PresetPlan]) -> dict[str, dict[str, Any]]:
    commands: dict[str, dict[str, Any]] = {}
    for plan in plans:
        if plan.category == "event":
            commands[plan.preset_id] = {"kind": "event", "on": {"preset": plan.preset_id}}
            continue
        commands[plan.preset_id] = {
            "kind": "state_toggle",
            "on": {"preset": plan.preset_id},
            "off": {"action": "clear_layer", "target_layer": plan.target_layer.value},
        }
    return commands


def _transformed_module_text(source_file: Path) -> str:
    return source_file.read_text(encoding="utf-8")


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
        )
    )
    if len(frame) != 12:
        raise ValueError(f"Effect {definition.id!r} rendered {len(frame)} LEDs instead of 12")


def _smoke_render_setup(definition: EffectDefinition) -> tuple[LayerId, PlaybackMode | None, int | None]:
    for layer_id, rule in definition.layer_rules.items():
        if not rule.allowed:
            continue
        playback_modes = rule.allowed_playback_modes or definition.capabilities.playback_modes or (PlaybackMode.SINGLE_RUN,)
        requested_duration_ms = None
        if rule.requires_finite_duration:
            requested_duration_ms = int(definition.defaults.get("duration_ms", definition.defaults.get("total_ms", 1000)) or 1000)
        return layer_id, playback_modes[0], requested_duration_ms
    raise ValueError(f"Effect {definition.id!r} does not allow any layer")


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
    "DEFAULT_PUBLISH_COPY",
    "DEFAULT_SOURCE_ID",
    "DEFAULT_SOURCES_ROOT",
    "build_default_effects",
    "build_standard_effect_packages",
    "build_standard_effect_set",
    "discover_standard_effects",
    "generate_standard_effect_sources",
]
