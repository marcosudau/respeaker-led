from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.effect_schema import EffectDefinition
from ..core.parameter_validation import normalize_values


@dataclass(slots=True, frozen=True)
class EffectPresetDefinition:
    source_id: str
    effect_id: str
    preset_id: str
    title: str | None = None
    description: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
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
            "params": dict(self.params),
            "tags": list(self.tags),
        }
        if self.title is not None:
            payload["title"] = self.title
        if self.description is not None:
            payload["description"] = self.description
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
    unknown_root = sorted(set(payload) - {"presets"})
    if unknown_root:
        raise ValueError(f"effect-presets.json contains unknown keys: {', '.join(unknown_root)}")

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
    allowed = {"title", "description", "params", "tags"}
    unknown = sorted(set(raw_definition) - allowed)
    if unknown:
        raise ValueError(f"Preset {preset_id!r} contains unknown keys: {', '.join(unknown)}")

    params = raw_definition.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ValueError(f"Preset {preset_id!r} field 'params' must be a JSON object")
    normalized_params = normalize_values(
        effect_definition.parameter_schema,
        params,
        field_prefix=f"presets.{preset_id}.params",
        require_required=False,
    )

    tags = raw_definition.get("tags", ())
    if tags is None:
        tags = ()
    if not isinstance(tags, (list, tuple)):
        raise ValueError(f"Preset {preset_id!r} field 'tags' must be a list")

    return EffectPresetDefinition(
        source_id=source_id,
        effect_id=effect_definition.id,
        preset_id=preset_id,
        title=None if raw_definition.get("title") is None else str(raw_definition.get("title")),
        description=None if raw_definition.get("description") is None else str(raw_definition.get("description")),
        params=normalized_params,
        tags=tuple(str(item) for item in tags),
    )
