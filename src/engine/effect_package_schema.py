from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.effect_schema import (
    ColorModel,
    CompositionMode,
    DefinitionType,
    EffectCapabilities,
    EffectDefinition,
    EffectParamDefinition,
    LayerId,
    LayerRule,
    OverlayMode,
    PlaybackMode,
    QueueMode,
)


@dataclass(slots=True, frozen=True)
class HashManifest:
    algorithm: str
    files: dict[str, str]


@dataclass(slots=True, frozen=True)
class EffectPackageManifest:
    format: str
    package_id: str
    source_id: str
    effect_id: str
    qualified_effect_id: str
    title: str
    description: str
    definition_type: DefinitionType
    overlay_mode: OverlayMode | None
    version: int
    runtime: str
    entry_module: str
    entry_class: str
    defaults: dict[str, Any]
    parameter_schema: dict[str, dict[str, Any]]
    runtime_input_schema: dict[str, dict[str, Any]]
    visual: dict[str, Any]
    input_sampling: dict[str, Any] | None
    layer_rules: dict[str, dict[str, Any]]
    capabilities: dict[str, Any]
    min_service_version: str
    tags: tuple[str, ...] = ()
    author: str | None = None
    vendor: str | None = None
    build_meta: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None
    compatible_hardware: tuple[str, ...] = ()
    license: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "format": self.format,
            "package_id": self.package_id,
            "source_id": self.source_id,
            "effect_id": self.effect_id,
            "qualified_effect_id": self.qualified_effect_id,
            "title": self.title,
            "description": self.description,
            "definition_type": self.definition_type.value,
            "overlay_mode": None if self.overlay_mode is None else self.overlay_mode.value,
            "version": self.version,
            "runtime": self.runtime,
            "entry_module": self.entry_module,
            "entry_class": self.entry_class,
            "defaults": _json_normalize(self.defaults),
            "parameter_schema": _json_normalize(self.parameter_schema),
            "runtime_input_schema": _json_normalize(self.runtime_input_schema),
            "visual": _json_normalize(self.visual),
            "input_sampling": _json_normalize(self.input_sampling),
            "layer_rules": _json_normalize(self.layer_rules),
            "capabilities": _json_normalize(self.capabilities),
            "min_service_version": self.min_service_version,
            "tags": list(self.tags),
        }
        if self.author is not None:
            payload["author"] = self.author
        if self.vendor is not None:
            payload["vendor"] = self.vendor
        if self.build_meta:
            payload["build_meta"] = _json_normalize(self.build_meta)
        if self.created_at is not None:
            payload["created_at"] = self.created_at
        if self.compatible_hardware:
            payload["compatible_hardware"] = list(self.compatible_hardware)
        if self.license is not None:
            payload["license"] = self.license
        return payload


@dataclass(slots=True, frozen=True)
class EffectSetManifest:
    format: str
    set_id: str
    source_id: str
    title: str
    version: int
    min_service_version: str
    effects: tuple[dict[str, Any], ...]
    description: str | None = None
    tags: tuple[str, ...] = ()
    author: str | None = None
    vendor: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "format": self.format,
            "set_id": self.set_id,
            "source_id": self.source_id,
            "title": self.title,
            "version": self.version,
            "min_service_version": self.min_service_version,
            "effects": [dict(item) for item in self.effects],
            "tags": list(self.tags),
        }
        if self.description is not None:
            payload["description"] = self.description
        if self.author is not None:
            payload["author"] = self.author
        if self.vendor is not None:
            payload["vendor"] = self.vendor
        return payload


def load_source_manifest(root: Path, stem: str) -> dict[str, Any]:
    import json

    from ..infrastructure.simple_yaml import parse_simple_yaml

    json_path = root / f"{stem}.json"
    yaml_path = root / f"{stem}.yaml"
    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))
    if yaml_path.exists():
        return parse_simple_yaml(yaml_path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Expected {stem}.json or {stem}.yaml in {root}")


def load_optional_source_manifest(root: Path, stem: str) -> dict[str, Any] | None:
    try:
        return load_source_manifest(root, stem)
    except FileNotFoundError:
        return None


def parse_hash_manifest(payload: dict[str, Any]) -> HashManifest:
    if not isinstance(payload, dict):
        raise ValueError("hashes.json must contain a JSON object")
    algorithm = str(payload.get("algorithm", "")).strip().lower()
    if algorithm != "sha256":
        raise ValueError(f"Unsupported hash algorithm: {algorithm!r}")
    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("hashes.json must define a non-empty 'files' mapping")
    normalized: dict[str, str] = {}
    for name, digest in files.items():
        normalized[str(name)] = str(digest).strip().lower()
    return HashManifest(algorithm=algorithm, files=normalized)


def parse_effect_package_manifest(payload: dict[str, Any]) -> EffectPackageManifest:
    if not isinstance(payload, dict):
        raise ValueError("manifest.json must contain a JSON object")
    required = [
        "format",
        "package_id",
        "source_id",
        "effect_id",
        "qualified_effect_id",
        "title",
        "description",
        "definition_type",
        "overlay_mode",
        "version",
        "runtime",
        "entry_module",
        "entry_class",
        "defaults",
        "parameter_schema",
        "runtime_input_schema",
        "visual",
        "input_sampling",
        "layer_rules",
        "capabilities",
        "min_service_version",
    ]
    _require_keys(payload, required, "manifest.json")
    optional = {
        "tags",
        "author",
        "vendor",
        "build_meta",
        "created_at",
        "compatible_hardware",
        "license",
    }
    _reject_unknown_keys(payload, set(required) | optional, "manifest.json")
    if payload["format"] != "lefx/2":
        raise ValueError(f"Unsupported LEFX format: {payload['format']!r}")
    definition_type = DefinitionType(str(payload["definition_type"]))
    raw_overlay_mode = payload["overlay_mode"]
    overlay_mode = None if raw_overlay_mode is None else OverlayMode(str(raw_overlay_mode))
    return EffectPackageManifest(
        format=str(payload["format"]),
        package_id=str(payload["package_id"]),
        source_id=str(payload["source_id"]),
        effect_id=str(payload["effect_id"]),
        qualified_effect_id=str(payload["qualified_effect_id"]),
        title=str(payload["title"]),
        description=str(payload["description"]),
        definition_type=definition_type,
        overlay_mode=overlay_mode,
        version=int(payload["version"]),
        runtime=str(payload["runtime"]),
        entry_module=str(payload["entry_module"]),
        entry_class=str(payload["entry_class"]),
        defaults=_copy_dict(payload["defaults"], "manifest.json.defaults"),
        parameter_schema=_copy_mapping_of_dicts(payload["parameter_schema"], "manifest.json.parameter_schema"),
        runtime_input_schema=_copy_mapping_of_dicts(
            payload["runtime_input_schema"],
            "manifest.json.runtime_input_schema",
        ),
        visual=_copy_dict(payload["visual"], "manifest.json.visual"),
        input_sampling=(
            None
            if payload["input_sampling"] is None
            else _copy_dict(payload["input_sampling"], "manifest.json.input_sampling")
        ),
        layer_rules=_copy_mapping_of_dicts(payload["layer_rules"], "manifest.json.layer_rules"),
        capabilities=_copy_dict(payload["capabilities"], "manifest.json.capabilities"),
        min_service_version=str(payload["min_service_version"]),
        tags=_copy_string_tuple(payload.get("tags", ())),
        author=None if payload.get("author") is None else str(payload.get("author")),
        vendor=None if payload.get("vendor") is None else str(payload.get("vendor")),
        build_meta=_copy_optional_dict(payload.get("build_meta")),
        created_at=None if payload.get("created_at") is None else str(payload.get("created_at")),
        compatible_hardware=_copy_string_tuple(payload.get("compatible_hardware", ())),
        license=None if payload.get("license") is None else str(payload.get("license")),
    )


def parse_effect_set_manifest(payload: dict[str, Any]) -> EffectSetManifest:
    if not isinstance(payload, dict):
        raise ValueError("set-manifest.json must contain a JSON object")
    required = [
        "format",
        "set_id",
        "source_id",
        "title",
        "version",
        "min_service_version",
        "effects",
    ]
    _require_keys(payload, required, "set-manifest.json")
    optional = {"description", "tags", "author", "vendor"}
    _reject_unknown_keys(payload, set(required) | optional, "set-manifest.json")
    if payload["format"] != "lefxset/2":
        raise ValueError(f"Unsupported LEFX Set format: {payload['format']!r}")
    raw_effects = payload["effects"]
    if not isinstance(raw_effects, list) or not raw_effects:
        raise ValueError("set-manifest.json field 'effects' must be a non-empty list")
    effects: list[dict[str, Any]] = []
    for item in raw_effects:
        if not isinstance(item, dict):
            raise ValueError("set-manifest.json field 'effects' must contain only objects")
        effects.append(dict(item))
    return EffectSetManifest(
        format=str(payload["format"]),
        set_id=str(payload["set_id"]),
        source_id=str(payload["source_id"]),
        title=str(payload["title"]),
        version=int(payload["version"]),
        min_service_version=str(payload["min_service_version"]),
        effects=tuple(effects),
        description=None if payload.get("description") is None else str(payload.get("description")),
        tags=_copy_string_tuple(payload.get("tags", ())),
        author=None if payload.get("author") is None else str(payload.get("author")),
        vendor=None if payload.get("vendor") is None else str(payload.get("vendor")),
    )


def serialize_effect_definition(definition: EffectDefinition) -> dict[str, Any]:
    return {
        "definition_type": definition.definition_type.value if definition.definition_type is not None else None,
        "overlay_mode": None if definition.overlay_mode is None else definition.overlay_mode.value,
        "defaults": _json_normalize(definition.defaults),
        "parameter_schema": {
            name: serialize_param_definition(param)
            for name, param in definition.parameter_schema.items()
        },
        "runtime_input_schema": {
            name: serialize_param_definition(param)
            for name, param in definition.runtime_input_schema.items()
        },
        "visual": {
            "color_model": definition.color_model.value,
            "composition": definition.composition.value,
            "animated": definition.animated,
            "directional": definition.directional,
        },
        "input_sampling": serialize_input_sampling(definition.input_sampling),
        "layer_rules": {
            layer_id.value: serialize_layer_rule(rule)
            for layer_id, rule in definition.layer_rules.items()
        },
        "capabilities": serialize_effect_capabilities(definition.capabilities),
        "title": definition.title,
        "description": definition.description,
        "version": definition.version,
        "tags": list(definition.tags),
    }


def serialize_param_definition(param: EffectParamDefinition) -> dict[str, Any]:
    return {
        "name": param.name,
        "type": param.type,
        "required": param.required,
        "default": _json_normalize(param.default),
        "description": param.description,
        "minimum": _json_normalize(param.minimum),
        "maximum": _json_normalize(param.maximum),
        "enum_values": list(param.enum_values),
        "unit": param.unit,
        "nullable": param.nullable,
        "aliases": list(param.aliases),
    }


def serialize_layer_rule(rule: LayerRule) -> dict[str, Any]:
    return {
        "allowed": rule.allowed,
        "allowed_playback_modes": [mode.value for mode in rule.allowed_playback_modes],
        "requires_finite_duration": rule.requires_finite_duration,
        "requires_indefinite_duration": rule.requires_indefinite_duration,
        "allows_transparency": rule.allows_transparency,
        "queue_mode": rule.queue_mode.value,
        "persistent_storage": rule.persistent_storage,
    }


def serialize_effect_capabilities(capabilities: EffectCapabilities) -> dict[str, Any]:
    return {
        "playback_modes": [mode.value for mode in capabilities.playback_modes],
        "supports_transparency": capabilities.supports_transparency,
        "supports_duration_override": capabilities.supports_duration_override,
        "supports_queueing": capabilities.supports_queueing,
        "preemptible": capabilities.preemptible,
        "restorable": capabilities.restorable,
        "data_driven": capabilities.data_driven,
    }


def serialize_input_sampling(policy: InputSamplingPolicy | None) -> dict[str, Any] | None:
    if policy is None:
        return None
    return {
        "mode": policy.mode.value,
        "provider_id": policy.provider_id,
        "interval_ms": policy.interval_ms,
        "heartbeat_interval_ms": policy.heartbeat_interval_ms,
        "max_missed_heartbeats": policy.max_missed_heartbeats,
    }


def _json_normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_normalize(item) for item in value]
    return value


def validate_manifest_matches_definition(manifest: EffectPackageManifest, definition: EffectDefinition) -> None:
    serialized = serialize_effect_definition(definition)
    if manifest.effect_id != definition.id:
        raise ValueError(
            f"Manifest effect_id {manifest.effect_id!r} does not match class definition id {definition.id!r}"
        )
    if manifest.qualified_effect_id != f"{manifest.source_id}::{manifest.effect_id}":
        raise ValueError("Manifest qualified_effect_id does not match source_id::effect_id")
    if manifest.definition_type.value != serialized["definition_type"]:
        raise ValueError("Manifest definition_type does not match class definition")
    if (
        None if manifest.overlay_mode is None else manifest.overlay_mode.value
    ) != serialized["overlay_mode"]:
        raise ValueError("Manifest overlay_mode does not match class definition")
    if manifest.title != serialized["title"]:
        raise ValueError("Manifest title does not match class definition")
    if manifest.description != serialized["description"]:
        raise ValueError("Manifest description does not match class definition")
    if manifest.version != serialized["version"]:
        raise ValueError("Manifest version does not match class definition")
    if manifest.defaults != serialized["defaults"]:
        raise ValueError("Manifest defaults do not match class definition")
    if manifest.parameter_schema != serialized["parameter_schema"]:
        raise ValueError("Manifest parameter_schema does not match class definition")
    if manifest.runtime_input_schema != serialized["runtime_input_schema"]:
        raise ValueError("Manifest runtime_input_schema does not match class definition")
    if manifest.visual != serialized["visual"]:
        raise ValueError("Manifest visual contract does not match class definition")
    if manifest.input_sampling != serialized["input_sampling"]:
        raise ValueError("Manifest input_sampling does not match class definition")
    if manifest.layer_rules != serialized["layer_rules"]:
        raise ValueError("Manifest layer_rules do not match class definition")
    if manifest.capabilities != serialized["capabilities"]:
        raise ValueError("Manifest capabilities do not match class definition")


def _require_keys(payload: dict[str, Any], required: list[str], label: str) -> None:
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"{label} is missing required keys: {', '.join(missing)}")


def _reject_unknown_keys(payload: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"{label} contains unknown keys: {', '.join(unknown)}")


def _copy_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return dict(value)


def _copy_optional_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("Optional metadata field must be a JSON object when provided")
    return dict(value)


def _copy_mapping_of_dicts(value: Any, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    normalized: dict[str, dict[str, Any]] = {}
    for key, item in value.items():
        if not isinstance(item, dict):
            raise ValueError(f"{label}.{key} must be a JSON object")
        normalized[str(key)] = dict(item)
    return normalized


def _copy_string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError("Expected a list of strings")
    return tuple(str(item) for item in value)
    InputMode,
    InputSamplingPolicy,
