from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any, Mapping

from .effect_schema import EffectDefinition, EffectParamDefinition
from .value_normalization import (
    ValueNormalizationError,
    format_color,
    parse_angle_degrees,
    parse_bool,
    parse_duration_ms,
    parse_ratio,
)


@dataclass(slots=True, frozen=True)
class ValidationIssue:
    code: str
    field: str
    message: str
    value: Any = None
    suggestions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "field": self.field,
            "message": self.message,
            "value": self.value,
        }
        if self.suggestions:
            payload["suggestions"] = list(self.suggestions)
        return payload


class ParameterValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("; ".join(issue.message for issue in issues))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": "validation_failed",
            "issues": [issue.to_dict() for issue in self.issues],
        }


def resolve_configuration(
    definition: EffectDefinition,
    *,
    preset: Mapping[str, Any] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    merged = dict(definition.defaults)
    merged.update(dict(preset or {}))
    merged.update(dict(overrides or {}))
    return normalize_values(
        definition.parameter_schema,
        merged,
        field_prefix="config",
        require_required=True,
    )


def normalize_runtime_inputs(
    definition: EffectDefinition,
    values: Mapping[str, Any] | None,
    *,
    require_required: bool = False,
) -> dict[str, Any]:
    return normalize_values(
        definition.runtime_input_schema,
        values,
        field_prefix="inputs",
        require_required=require_required,
    )


def normalize_values(
    schema: Mapping[str, EffectParamDefinition],
    values: Mapping[str, Any] | None,
    *,
    field_prefix: str,
    require_required: bool,
) -> dict[str, Any]:
    raw = dict(values or {})
    issues: list[ValidationIssue] = []
    alias_map = {
        alias: name
        for name, definition in schema.items()
        for alias in definition.aliases
    }
    for alias, name in alias_map.items():
        if alias not in raw:
            continue
        if name in raw:
            issues.append(
                ValidationIssue(
                    code="conflicting_fields",
                    field=f"{field_prefix}.{alias}",
                    value=raw[alias],
                    message=f"Fields {name!r} and its alias {alias!r} cannot be used together",
                )
            )
            raw.pop(alias)
            continue
        raw[name] = raw.pop(alias)

    accepted_names = sorted(set(schema) | set(alias_map))
    for name in sorted(set(raw) - set(schema)):
        suggestions = tuple(difflib.get_close_matches(name, accepted_names, n=3, cutoff=0.55))
        issues.append(
            ValidationIssue(
                code="unknown_field",
                field=f"{field_prefix}.{name}",
                value=raw[name],
                message=f"Unknown field {name!r}",
                suggestions=suggestions,
            )
        )

    normalized: dict[str, Any] = {}
    for name, param in schema.items():
        if name not in raw:
            if require_required and param.required and param.default is None:
                issues.append(
                    ValidationIssue(
                        code="missing_required",
                        field=f"{field_prefix}.{name}",
                        message=f"Missing required field {name!r}",
                    )
                )
            continue
        try:
            normalized[name] = normalize_parameter_value(param, raw[name])
        except (ValueError, TypeError, ValueNormalizationError) as exc:
            suggestions = exc.suggestions if isinstance(exc, ValueNormalizationError) else ()
            code = exc.code if isinstance(exc, ValueNormalizationError) else "invalid_value"
            issues.append(
                ValidationIssue(
                    code=code,
                    field=f"{field_prefix}.{name}",
                    value=raw[name],
                    message=str(exc),
                    suggestions=tuple(suggestions),
                )
            )

    if issues:
        raise ParameterValidationError(issues)
    return normalized


def normalize_parameter_value(definition: EffectParamDefinition, value: Any) -> Any:
    if value is None and definition.nullable:
        return None
    kind = definition.type
    if kind == "bool":
        normalized = parse_bool(value)
    elif kind == "int":
        if isinstance(value, bool):
            raise ValueError(f"{definition.name} must be an integer")
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{definition.name} must be an integer") from exc
    elif kind == "float":
        if isinstance(value, bool):
            raise ValueError(f"{definition.name} must be numeric")
        if (
            isinstance(value, str)
            and value.strip().endswith("%")
            and definition.minimum == 0.0
            and definition.maximum == 1.0
        ):
            normalized = parse_ratio(value)
        elif (
            isinstance(value, str)
            and value.strip().endswith("%")
            and definition.minimum == 0.0
            and definition.maximum == 100.0
        ):
            try:
                normalized = float(value.strip()[:-1])
            except ValueError as exc:
                raise ValueError(f"{definition.name} must be numeric or a percentage") from exc
        else:
            try:
                normalized = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{definition.name} must be numeric") from exc
    elif kind == "duration_ms":
        normalized = parse_duration_ms(
            value,
            minimum=max(0, int(definition.minimum or 0)),
        )
    elif kind == "angle_deg":
        normalized = parse_angle_degrees(value)
    elif kind == "enum":
        normalized = _normalize_enum(definition, value)
    elif kind == "color":
        normalized = format_color(value)
    elif kind == "color_list":
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{definition.name} must be a list of colors")
        normalized = [format_color(item) for item in value]
        if definition.minimum is not None and len(normalized) < definition.minimum:
            raise ValueError(
                f"{definition.name} must contain at least {int(definition.minimum)} colors"
            )
        if definition.maximum is not None and len(normalized) > definition.maximum:
            raise ValueError(
                f"{definition.name} must contain at most {int(definition.maximum)} colors"
            )
    elif kind == "gradient":
        normalized = _normalize_gradient(definition, value)
    elif kind == "color_range":
        normalized = _normalize_color_range(definition, value)
    else:
        raise ValueError(f"Unsupported parameter type {kind!r} for {definition.name!r}")

    if isinstance(normalized, (int, float)) and not isinstance(normalized, bool):
        if definition.minimum is not None and normalized < definition.minimum:
            raise ValueError(f"{definition.name} must be >= {definition.minimum}")
        if definition.maximum is not None and normalized > definition.maximum:
            raise ValueError(f"{definition.name} must be <= {definition.maximum}")
    return normalized


def _normalize_enum(definition: EffectParamDefinition, value: Any) -> Any:
    if value in definition.enum_values:
        return value
    if isinstance(value, str):
        matches = [
            candidate
            for candidate in definition.enum_values
            if isinstance(candidate, str) and candidate.casefold() == value.strip().casefold()
        ]
        if len(matches) == 1:
            return matches[0]
    expected = ", ".join(repr(item) for item in definition.enum_values)
    raise ValueError(f"{definition.name} must be one of: {expected}")


def _normalize_gradient(definition: EffectParamDefinition, value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)) or not 2 <= len(value) <= 16:
        raise ValueError(f"{definition.name} must contain between 2 and 16 color stops")
    stops: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping) or set(item) != {"at", "color"}:
            raise ValueError(
                f"{definition.name}[{index}] must contain exactly 'at' and 'color'"
            )
        at = float(item["at"])
        if not 0.0 <= at <= 1.0:
            raise ValueError(f"{definition.name}[{index}].at must be between 0 and 1")
        stops.append({"at": at, "color": format_color(item["color"])})
    positions = [item["at"] for item in stops]
    if positions != sorted(positions) or positions[0] != 0.0 or positions[-1] != 1.0:
        raise ValueError(
            f"{definition.name} stops must be sorted and include positions 0 and 1"
        )
    return stops


def _normalize_color_range(definition: EffectParamDefinition, value: Any) -> dict[str, list[float]]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{definition.name} must be an HSV range object")
    required = {"hue", "saturation", "brightness"}
    if set(value) != required:
        raise ValueError(
            f"{definition.name} must contain exactly hue, saturation and brightness"
        )
    limits = {
        "hue": (0.0, 360.0),
        "saturation": (0.0, 1.0),
        "brightness": (0.0, 1.0),
    }
    normalized: dict[str, list[float]] = {}
    for name, (minimum, maximum) in limits.items():
        raw = value[name]
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            raise ValueError(f"{definition.name}.{name} must be a [minimum, maximum] pair")
        low, high = float(raw[0]), float(raw[1])
        if low > high or low < minimum or high > maximum:
            raise ValueError(
                f"{definition.name}.{name} must satisfy {minimum} <= minimum <= maximum <= {maximum}"
            )
        normalized[name] = [low, high]
    return normalized
