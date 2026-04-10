from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar


class LayerId(str, Enum):
    BACKGROUND_STATE_LAYER = "BACKGROUND_STATE_LAYER"
    STATE_LAYER = "STATE_LAYER"
    MAIN_LAYER = "MAIN_LAYER"
    TEMP_OVERLAY_LAYER = "TEMP_OVERLAY_LAYER"
    ONGOING_OVERLAY_LAYER = "ONGOING_OVERLAY_LAYER"
    EVENT_LAYER = "EVENT_LAYER"


_LAYER_ID_ALIASES: dict[str, LayerId] = {
    "background": LayerId.BACKGROUND_STATE_LAYER,
    "background_state": LayerId.BACKGROUND_STATE_LAYER,
    "background_state_layer": LayerId.BACKGROUND_STATE_LAYER,
    "state": LayerId.STATE_LAYER,
    "state_layer": LayerId.STATE_LAYER,
    "main": LayerId.MAIN_LAYER,
    "main_layer": LayerId.MAIN_LAYER,
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
    LayerId.MAIN_LAYER: 300,
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
    parameter_schema: dict[str, EffectParamDefinition] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)
    layer_rules: dict[LayerId, LayerRule] = field(default_factory=dict)
    capabilities: EffectCapabilities = field(default_factory=EffectCapabilities)
    tags: tuple[str, ...] = ()
    version: int = 1


@dataclass(slots=True)
class EffectInvocation:
    invocation_id: str
    effect_id: str
    target_layer: LayerId
    params: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    transparent: bool = False
    priority: int | None = None
    playback_mode: PlaybackMode | None = None
    requested_duration_ms: int | None = None
    source: str | None = None
    created_at: float = 0.0
    replace_existing: bool = True

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


class BaseEffect(ABC):
    definition: ClassVar[EffectDefinition]

    @classmethod
    def get_definition(cls) -> EffectDefinition:
        return cls.definition

    @abstractmethod
    def render(self, ctx: RenderContext) -> list[int | None]:
        raise NotImplementedError
