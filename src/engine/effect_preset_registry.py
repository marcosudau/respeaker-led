from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.effect_schema import EffectDefinition, LayerId, parse_layer_id


_PRESET_CATEGORIES = {"state", "effect", "overlay", "event"}
_CATEGORY_LAYER_RULES: dict[str, set[LayerId]] = {
    "state": {LayerId.BACKGROUND_STATE_LAYER, LayerId.STATE_LAYER},
    "effect": {LayerId.MAIN_LAYER},
    "overlay": {LayerId.TEMP_OVERLAY_LAYER, LayerId.ONGOING_OVERLAY_LAYER},
    "event": {LayerId.EVENT_LAYER},
}


@dataclass(slots=True, frozen=True)
class EffectPresetDefinition:
    source_id: str
    effect_id: str
    preset_id: str
    category: str
    target_layer: LayerId
    title: str | None = None
    description: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    duration_ms: int | None = None
    priority: int | None = None
    enqueue: bool = False
    replace_existing: bool = True
    tags: tuple[str, ...] = ()

    @property
    def qualified_preset_id(self) -> str:
        return f"{self.source_id}::{self.preset_id}"

    @property
    def qualified_effect_id(self) -> str:
        return f"{self.source_id}::{self.effect_id}"

    def serialize(self) -> dict[str, Any]:
        payload = {
            "source_id": self.source_id,
            "effect_id": self.effect_id,
            "qualified_effect_id": self.qualified_effect_id,
            "preset_id": self.preset_id,
            "qualified_preset_id": self.qualified_preset_id,
            "category": self.category,
            "target_layer": self.target_layer.value,
            "params": dict(self.params),
            "enqueue": self.enqueue,
            "replace_existing": self.replace_existing,
            "tags": list(self.tags),
        }
        if self.title is not None:
            payload["title"] = self.title
        if self.description is not None:
            payload["description"] = self.description
        if self.duration_ms is not None:
            payload["duration_ms"] = self.duration_ms
        if self.priority is not None:
            payload["priority"] = self.priority
        return payload


class EffectPresetRegistry:
    def __init__(self) -> None:
        self._presets_by_source: dict[str, dict[str, EffectPresetDefinition]] = {}

    def register_many(self, source_id: str, presets: list[EffectPresetDefinition]) -> None:
        scoped = self._presets_by_source.setdefault(source_id, {})
        for preset in presets:
            if preset.preset_id in scoped:
                raise ValueError(f"Duplicate preset id detected for source {source_id!r}: {preset.preset_id!r}")
            scoped[preset.preset_id] = preset

    def remove_source(self, source_id: str) -> None:
        self._presets_by_source.pop(source_id, None)

    def get(self, source_id: str, preset_id: str) -> EffectPresetDefinition:
        return self._presets_by_source[source_id][preset_id]

    def list_presets(self, source_id: str | None = None, effect_id: str | None = None) -> list[EffectPresetDefinition]:
        if source_id is not None:
            presets = list(self._presets_by_source.get(source_id, {}).values())
        else:
            presets = []
            for scoped_source in sorted(self._presets_by_source):
                presets.extend(self._presets_by_source[scoped_source].values())
        if effect_id is not None:
            presets = [preset for preset in presets if preset.effect_id == effect_id]
        return sorted(presets, key=lambda item: (item.source_id, item.effect_id, item.preset_id))


def parse_effect_preset_definitions(
    source_id: str,
    effect_definition: EffectDefinition,
    payload: dict[str, Any],
) -> list[EffectPresetDefinition]:
    if not isinstance(payload, dict):
        raise ValueError("effect-presets.json must contain a JSON object")

    raw_presets = payload.get("presets")
    if not isinstance(raw_presets, dict) or not raw_presets:
        raise ValueError("effect-presets.json must define a non-empty 'presets' object")

    presets: list[EffectPresetDefinition] = []
    seen: set[str] = set()
    for preset_id, raw_definition in raw_presets.items():
        normalized_id = str(preset_id or "").strip()
        if not normalized_id:
            raise ValueError("Preset ids must be non-empty")
        if normalized_id in seen:
            raise ValueError(f"Duplicate preset id detected: {normalized_id!r}")
        seen.add(normalized_id)
        presets.append(parse_effect_preset_definition(source_id, effect_definition, normalized_id, raw_definition))
    return presets


def parse_effect_preset_definition(
    source_id: str,
    effect_definition: EffectDefinition,
    preset_id: str,
    raw_definition: Any,
) -> EffectPresetDefinition:
    if not isinstance(raw_definition, dict):
        raise ValueError(f"Preset {preset_id!r} must be a JSON object")

    category = str(raw_definition.get("category", "")).strip().lower()
    if category not in _PRESET_CATEGORIES:
        raise ValueError(f"Preset {preset_id!r} has unsupported category: {category!r}")
    if not preset_id.startswith(f"{category}_"):
        raise ValueError(
            f"Preset {preset_id!r} must use the '{category}_' prefix to match its category"
        )

    if "target_layer" not in raw_definition:
        raise ValueError(f"Preset {preset_id!r} must define 'target_layer'")
    target_layer = parse_layer_id(raw_definition["target_layer"])
    allowed_layers = _CATEGORY_LAYER_RULES[category]
    if target_layer not in allowed_layers:
        expected = ", ".join(layer.value for layer in sorted(allowed_layers, key=lambda item: item.value))
        raise ValueError(
            f"Preset {preset_id!r} with category {category!r} must target one of: {expected}"
        )

    layer_rule = effect_definition.layer_rules.get(target_layer)
    if layer_rule is None or not layer_rule.allowed:
        raise ValueError(
            f"Preset {preset_id!r} targets {target_layer.value}, but effect {effect_definition.id!r} does not allow that layer"
        )

    raw_effect = raw_definition.get("effect")
    if raw_effect is not None:
        normalized_effect = str(raw_effect).strip()
        local_effect_id = effect_definition.id
        qualified_effect_id = f"{source_id}::{local_effect_id}"
        if normalized_effect not in {local_effect_id, qualified_effect_id}:
            raise ValueError(
                f"Preset {preset_id!r} references effect {normalized_effect!r}, expected {local_effect_id!r} or {qualified_effect_id!r}"
            )

    params = raw_definition.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ValueError(f"Preset {preset_id!r} field 'params' must be a JSON object")
    normalized_params = dict(params)
    _validate_effect_params(effect_definition, preset_id, normalized_params)

    duration_ms = raw_definition.get("duration_ms")
    if duration_ms is not None:
        duration_ms = int(duration_ms)
        if duration_ms <= 0:
            raise ValueError(f"Preset {preset_id!r} field 'duration_ms' must be > 0")

    priority = raw_definition.get("priority")
    if priority is not None:
        priority = int(priority)

    tags = raw_definition.get("tags", ())
    if tags is None:
        tags = ()
    if not isinstance(tags, (list, tuple)):
        raise ValueError(f"Preset {preset_id!r} field 'tags' must be a list")

    return EffectPresetDefinition(
        source_id=source_id,
        effect_id=effect_definition.id,
        preset_id=preset_id,
        category=category,
        target_layer=target_layer,
        title=None if raw_definition.get("title") is None else str(raw_definition.get("title")),
        description=None if raw_definition.get("description") is None else str(raw_definition.get("description")),
        params=normalized_params,
        duration_ms=duration_ms,
        priority=priority,
        enqueue=bool(raw_definition.get("enqueue", False)),
        replace_existing=bool(raw_definition.get("replace_existing", True)),
        tags=tuple(str(item) for item in tags),
    )


def _validate_effect_params(effect_definition: EffectDefinition, preset_id: str, params: dict[str, Any]) -> None:
    schema = effect_definition.parameter_schema
    for name, value in params.items():
        if name not in schema:
            raise ValueError(f"Preset {preset_id!r} defines unknown effect parameter: {name!r}")
        _validate_param_value(preset_id, schema[name], value)


def _validate_param_value(preset_id: str, definition, value: Any) -> None:
    label = f"Preset {preset_id!r} parameter {definition.name!r}"
    kind = definition.type
    if kind == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"{label} must be a boolean")
    elif kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} must be an integer")
    elif kind in {"float", "duration_ms"}:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{label} must be numeric")
    elif kind == "enum":
        if value not in set(definition.enum_values):
            expected = ", ".join(repr(item) for item in definition.enum_values)
            raise ValueError(f"{label} must be one of: {expected}")
    elif kind == "color":
        if not isinstance(value, (int, str)):
            raise ValueError(f"{label} must be a color string or integer")
    elif kind == "color_list":
        if not isinstance(value, list) or not all(isinstance(item, (int, str)) for item in value):
            raise ValueError(f"{label} must be a list of color strings or integers")

    if definition.minimum is not None and isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < definition.minimum:
            raise ValueError(f"{label} must be >= {definition.minimum}")
    if definition.maximum is not None and isinstance(value, (int, float)) and not isinstance(value, bool):
        if value > definition.maximum:
            raise ValueError(f"{label} must be <= {definition.maximum}")
