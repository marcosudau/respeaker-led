from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar


class LayerId(str, Enum):
    BACKGROUND_STATE_LAYER = "BACKGROUND_STATE_LAYER"
    STATE_LAYER = "STATE_LAYER"
    TEMP_OVERLAY_LAYER = "TEMP_OVERLAY_LAYER"
    ONGOING_OVERLAY_LAYER = "ONGOING_OVERLAY_LAYER"
    EVENT_LAYER = "EVENT_LAYER"


_LAYER_ID_ALIASES: dict[str, LayerId] = {
    "background": LayerId.BACKGROUND_STATE_LAYER,
    "background_state": LayerId.BACKGROUND_STATE_LAYER,
    "background_state_layer": LayerId.BACKGROUND_STATE_LAYER,
    "state": LayerId.STATE_LAYER,
    "state_layer": LayerId.STATE_LAYER,
    "temp_overlay": LayerId.TEMP_OVERLAY_LAYER,
    "temp_overlay_layer": LayerId.TEMP_OVERLAY_LAYER,
    "ongoing_overlay": LayerId.ONGOING_OVERLAY_LAYER,
    "ongoing_overlay_layer": LayerId.ONGOING_OVERLAY_LAYER,
    "event": LayerId.EVENT_LAYER,
    "event_layer": LayerId.EVENT_LAYER,
}


def parse_layer_id(value: str | LayerId) -> LayerId:
    if isinstance(value, LayerId):
        return value

    normalized = str(value or "").strip().lower().replace("-", "_")
    if normalized in _LAYER_ID_ALIASES:
        return _LAYER_ID_ALIASES[normalized]

    valid_values = ", ".join(layer.value for layer in LayerId)
    raise ValueError(f"Unknown layer id: {value!r}. Expected one of: {valid_values}")


class PlaybackMode(str, Enum):
    SINGLE_RUN = "single_run"
    LOOP = "loop"
    PERSISTENT = "persistent"


class DefinitionType(str, Enum):
    STATE = "state"
    OVERLAY = "overlay"
    EVENT = "event"


class OverlayMode(str, Enum):
    CONTROLLED = "controlled"
    TIMED = "timed"


class InputMode(str, Enum):
    PUSH = "push"
    PULL = "pull"


class ColorModel(str, Enum):
    NONE = "none"
    MONO = "mono"
    DUAL = "dual"
    PALETTE = "palette"
    GRADIENT = "gradient"
    RANDOM_RANGE = "random_range"


class CompositionMode(str, Enum):
    OPAQUE = "opaque"
    TRANSPARENT = "transparent"


class CommandKind(str, Enum):
    SET_EFFECT = "set_effect"
    CLEAR_LAYER = "clear_layer"
    SET_LAYER_ENABLED = "set_layer_enabled"
    RESET_ENGINE = "reset_engine"


class QueueMode(str, Enum):
    FORBIDDEN = "forbidden"
    REPLACE = "replace"
    APPEND = "append"
    PRIORITY_FIFO = "priority_fifo"


DEFAULT_LAYER_PRIORITIES: dict[LayerId, int] = {
    LayerId.BACKGROUND_STATE_LAYER: 100,
    LayerId.STATE_LAYER: 200,
    LayerId.TEMP_OVERLAY_LAYER: 400,
    LayerId.ONGOING_OVERLAY_LAYER: 500,
    LayerId.EVENT_LAYER: 600,
}


@dataclass(slots=True, frozen=True)
class EffectParamDefinition:
    name: str
    type: str
    required: bool = False
    default: Any = None
    description: str = ""
    minimum: float | int | None = None
    maximum: float | int | None = None
    enum_values: tuple[Any, ...] = ()
    unit: str | None = None
    nullable: bool = False
    aliases: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class InputSamplingPolicy:
    mode: InputMode = InputMode.PUSH
    provider_id: str | None = None
    interval_ms: int = 0
    heartbeat_interval_ms: int = 1000
    max_missed_heartbeats: int = 3

    @property
    def failure_after_ms(self) -> int:
        return self.heartbeat_interval_ms * self.max_missed_heartbeats


@dataclass(slots=True, frozen=True)
class EffectCapabilities:
    playback_modes: tuple[PlaybackMode, ...] = (PlaybackMode.SINGLE_RUN,)
    supports_transparency: bool = False
    supports_duration_override: bool = False
    supports_queueing: bool = False
    preemptible: bool = True
    restorable: bool = False
    data_driven: bool = False


@dataclass(slots=True, frozen=True)
class LayerRule:
    allowed: bool = True
    allowed_playback_modes: tuple[PlaybackMode, ...] = ()
    requires_finite_duration: bool | None = None
    requires_indefinite_duration: bool | None = None
    allows_transparency: bool = False
    queue_mode: QueueMode = QueueMode.FORBIDDEN
    persistent_storage: bool = False


@dataclass(slots=True, frozen=True)
class EffectDefinition:
    id: str
    title: str
    description: str
    definition_type: DefinitionType | None = None
    overlay_mode: OverlayMode | None = None
    parameter_schema: dict[str, EffectParamDefinition] = field(default_factory=dict)
    runtime_input_schema: dict[str, EffectParamDefinition] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)
    layer_rules: dict[LayerId, LayerRule] = field(default_factory=dict)
    capabilities: EffectCapabilities = field(default_factory=EffectCapabilities)
    tags: tuple[str, ...] = ()
    version: int = 1
    color_model: ColorModel = ColorModel.NONE
    composition: CompositionMode = CompositionMode.OPAQUE
    animated: bool = False
    directional: bool = False
    input_sampling: InputSamplingPolicy | None = None

    def effective_input_sampling(self) -> InputSamplingPolicy | None:
        if (
            self.definition_type is DefinitionType.OVERLAY
            and self.overlay_mode is OverlayMode.CONTROLLED
            and self.runtime_input_schema
        ):
            return self.input_sampling or InputSamplingPolicy()
        return None


def validate_definition_contract(definition: EffectDefinition) -> None:
    if definition.definition_type is None:
        raise ValueError(f"Definition {definition.id!r} must declare definition_type")

    allowed_layers = {
        DefinitionType.STATE: {
            LayerId.BACKGROUND_STATE_LAYER,
            LayerId.STATE_LAYER,
        },
        DefinitionType.OVERLAY: {
            LayerId.TEMP_OVERLAY_LAYER
            if definition.overlay_mode is OverlayMode.TIMED
            else LayerId.ONGOING_OVERLAY_LAYER
        },
        DefinitionType.EVENT: {LayerId.EVENT_LAYER},
    }[definition.definition_type]

    declared_layers = {layer for layer, rule in definition.layer_rules.items() if rule.allowed}
    if not declared_layers:
        raise ValueError(f"Definition {definition.id!r} must allow at least one internal layer")
    invalid_layers = declared_layers - allowed_layers
    if invalid_layers:
        invalid = ", ".join(sorted(layer.value for layer in invalid_layers))
        raise ValueError(
            f"Definition {definition.id!r} of type {definition.definition_type.value!r} "
            f"cannot use layers: {invalid}"
        )

    if definition.definition_type is DefinitionType.OVERLAY:
        if definition.overlay_mode is None:
            raise ValueError(f"Overlay definition {definition.id!r} must declare overlay_mode")
    elif definition.overlay_mode is not None:
        raise ValueError(
            f"Definition {definition.id!r} of type {definition.definition_type.value!r} "
            "must not declare overlay_mode"
        )

    if definition.definition_type is DefinitionType.EVENT or (
        definition.definition_type is DefinitionType.OVERLAY
        and definition.overlay_mode is OverlayMode.TIMED
    ):
        rules = [definition.layer_rules[layer] for layer in declared_layers]
        if not all(rule.requires_finite_duration is True for rule in rules):
            raise ValueError(f"Definition {definition.id!r} must require a finite duration")
        duration_fields = {"duration_ms", "total_ms"} & set(definition.parameter_schema)
        if not duration_fields:
            raise ValueError(
                f"Definition {definition.id!r} must declare duration_ms or total_ms"
            )

    if definition.definition_type is DefinitionType.STATE or (
        definition.definition_type is DefinitionType.OVERLAY
        and definition.overlay_mode is OverlayMode.CONTROLLED
    ):
        rules = [definition.layer_rules[layer] for layer in declared_layers]
        if not all(rule.requires_indefinite_duration is True for rule in rules):
            raise ValueError(f"Definition {definition.id!r} must require an indefinite duration")

    if definition.runtime_input_schema and not (
        definition.definition_type is DefinitionType.OVERLAY
        and definition.overlay_mode is OverlayMode.CONTROLLED
    ):
        raise ValueError(
            f"Definition {definition.id!r} cannot declare mutable runtime inputs; "
            "only controlled overlays support them"
        )

    if definition.input_sampling is not None and not (
        definition.definition_type is DefinitionType.OVERLAY
        and definition.overlay_mode is OverlayMode.CONTROLLED
    ):
        raise ValueError(
            f"Definition {definition.id!r} cannot declare input sampling; "
            "only controlled overlays support it"
        )
    if definition.input_sampling is not None:
        policy = definition.input_sampling
        if policy.provider_id is not None and (
            policy.mode is not InputMode.PULL or not policy.provider_id.strip()
        ):
            raise ValueError(
                f"Definition {definition.id!r} input provider_id requires pull mode "
                "and must not be empty"
            )
        if policy.interval_ms < 0:
            raise ValueError(f"Definition {definition.id!r} sampling interval_ms must be >= 0")
        if policy.heartbeat_interval_ms < 100:
            raise ValueError(
                f"Definition {definition.id!r} heartbeat_interval_ms must be >= 100"
            )
        if policy.max_missed_heartbeats < 1:
            raise ValueError(
                f"Definition {definition.id!r} max_missed_heartbeats must be >= 1"
            )
        if policy.mode is InputMode.PULL and not definition.runtime_input_schema:
            raise ValueError(
                f"Definition {definition.id!r} uses pull sampling but declares no runtime inputs"
            )

    if definition.animated:
        speed = definition.parameter_schema.get("speed")
        if speed is None:
            raise ValueError(f"Animated definition {definition.id!r} must declare config.speed")

    if definition.directional:
        reverse = definition.parameter_schema.get("reverse")
        if reverse is None or reverse.type != "bool":
            raise ValueError(
                f"Directional definition {definition.id!r} must declare boolean config.reverse"
            )

    _validate_color_model(definition)
    _validate_schema(definition, definition.parameter_schema, label="parameter")
    _validate_schema(definition, definition.runtime_input_schema, label="runtime input")

    unknown_defaults = set(definition.defaults) - set(definition.parameter_schema)
    if unknown_defaults:
        names = ", ".join(sorted(unknown_defaults))
        raise ValueError(f"Definition {definition.id!r} has defaults for unknown parameters: {names}")


def _validate_schema(
    definition: EffectDefinition,
    schema: dict[str, EffectParamDefinition],
    *,
    label: str,
) -> None:
    canonical_names = set(schema)
    aliases: dict[str, str] = {}
    for key, value in schema.items():
        if not isinstance(value, EffectParamDefinition):
            raise TypeError(f"Definition {definition.id!r} {label} {key!r} is invalid")
        if key != value.name:
            raise ValueError(
                f"Definition {definition.id!r} {label} schema key/name mismatch: "
                f"{key!r} != {value.name!r}"
            )
        for alias in value.aliases:
            normalized = str(alias).strip()
            if not normalized or normalized == key:
                raise ValueError(
                    f"Definition {definition.id!r} {label} {key!r} has invalid alias {alias!r}"
                )
            if normalized in canonical_names:
                raise ValueError(
                    f"Definition {definition.id!r} {label} alias {normalized!r} "
                    "collides with a canonical field"
                )
            owner = aliases.get(normalized)
            if owner is not None:
                raise ValueError(
                    f"Definition {definition.id!r} {label} alias {normalized!r} "
                    f"is shared by {owner!r} and {key!r}"
                )
            aliases[normalized] = key


def _validate_color_model(definition: EffectDefinition) -> None:
    names = set(definition.parameter_schema)
    required_by_model = {
        ColorModel.NONE: set(),
        ColorModel.MONO: {"color"},
        ColorModel.DUAL: {"color", "secondary_color"},
        ColorModel.PALETTE: {"colors"},
        ColorModel.GRADIENT: {"gradient"},
        ColorModel.RANDOM_RANGE: {"color_range", "random_seed"},
    }
    required = required_by_model[definition.color_model]
    missing = required - names
    if missing:
        raise ValueError(
            f"Definition {definition.id!r} color model {definition.color_model.value!r} "
            f"requires config fields: {', '.join(sorted(missing))}"
        )

    color_fields = {
        "color",
        "secondary_color",
        "colors",
        "gradient",
        "color_range",
        "random_seed",
    }
    if definition.color_model is ColorModel.NONE and names & color_fields:
        raise ValueError(
            f"Definition {definition.id!r} declares color configuration but uses color model 'none'"
        )
    if definition.color_model is not ColorModel.NONE:
        brightness = definition.parameter_schema.get("brightness")
        if (
            brightness is None
            or brightness.type != "float"
            or brightness.minimum != 0.0
            or brightness.maximum != 1.0
        ):
            raise ValueError(
                f"Definition {definition.id!r} must declare config.brightness "
                "as a float in the range 0..1"
            )
@dataclass(slots=True)
class EffectInvocation:
    invocation_id: str
    effect_id: str
    target_layer: LayerId
    params: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    transparent: bool = False
    priority: int | None = None
    playback_mode: PlaybackMode | None = None
    requested_duration_ms: int | None = None
    source: str | None = None
    created_at: float = 0.0
    replace_existing: bool = True
    input_last_attempt_at: float | None = None
    input_last_success_at: float | None = None
    input_error: str | None = None

    def effective_priority(self) -> int:
        return DEFAULT_LAYER_PRIORITIES[self.target_layer] if self.priority is None else int(self.priority)


@dataclass(slots=True)
class LayerState:
    layer_id: LayerId
    priority: int
    enabled: bool = True
    active_invocation: EffectInvocation | None = None
    queue: list[EffectInvocation] = field(default_factory=list)


@dataclass(slots=True)
class NormalizedCommand:
    kind: CommandKind
    target_layer: LayerId | None = None
    effect_id: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)
    enabled: bool | None = None
    priority: int | None = None
    source: str | None = None
    timestamp: float | None = None
    enqueue: bool = False
    replace_existing: bool = True


@dataclass(slots=True, frozen=True)
class PersistedLayerState:
    schema_version: int
    layer_id: LayerId
    effect_id: str
    params: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    transparent: bool = False
    saved_at: float = 0.0


@dataclass(slots=True)
class RenderContext:
    now: float
    led_count: int
    layer_id: LayerId
    definition: EffectDefinition
    invocation: EffectInvocation
    params: dict[str, Any]
    inputs: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class InputContext:
    now: float
    led_count: int
    config: dict[str, Any]
    previous_inputs: dict[str, Any]


class BaseEffect(ABC):
    definition: ClassVar[EffectDefinition]

    @classmethod
    def get_definition(cls) -> EffectDefinition:
        return cls.definition

    def sample_inputs(self, ctx: InputContext) -> dict[str, Any] | None:
        del ctx
        return None

    @abstractmethod
    def render(self, ctx: RenderContext) -> list[int | None]:
        raise NotImplementedError
