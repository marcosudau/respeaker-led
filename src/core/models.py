from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


LED_COUNT = 12
Color = int
FrameProvider = Callable[[float], list[Color | None]]

DEFAULT_BASE_STATE = "idle"
BASE_STATE_NAMES = (
    "offline",
    "idle",
    "listening",
    "recording",
    "transcribing",
    "error",
    "service_starting",
    "service_stopping",
    "wakeword_armed",
    "wakeword_detected",
    "ready",
    "processing",
    "muted",
    "realtime_active",
)
EVENT_NAMES = (
    "trigger_received",
    "text_committed",
    "warning",
    "error_flash",
    "timeout_imminent",
    "wakeword_ack",
    "notification",
)


@dataclass(slots=True)
class Visual:
    type: str
    params: dict[str, Any] = field(default_factory=dict)
    exclusive: bool = False


@dataclass(slots=True)
class LayerVisual:
    name: str
    priority: int
    visual: Visual


@dataclass(slots=True)
class BaseState:
    name: str = DEFAULT_BASE_STATE
    payload: dict[str, Any] = field(default_factory=dict)
    updated_at: float = 0.0


@dataclass(slots=True)
class StateLayerState:
    mode: str = "off"
    visual: Visual | None = None
    enabled: bool = True


@dataclass(slots=True)
class ActiveVisualState:
    id: str
    mode: str
    payload: dict[str, Any] = field(default_factory=dict)
    visual: Visual | None = None
    valid: bool = True
    updated_at: float = 0.0


MainLayerState = ActiveVisualState


@dataclass(slots=True)
class Event:
    id: str
    name: str
    visual: Visual
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 100
    created_at: float = 0.0
    duration: float | None = 3.0
    exclusive: bool = True
    active: bool = True

    def is_expired(self, now: float) -> bool:
        if not self.active:
            return True
        if self.duration is None:
            return False
        return now >= self.created_at + self.duration

    @property
    def kind(self) -> str:
        return self.name


@dataclass(slots=True)
class CountdownState:
    total_ms: int
    remaining_ms: int
    started_at: float
    deadline: float
    follow_up_state: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    active: bool = True

    def is_expired(self, now: float) -> bool:
        return not self.active or now >= self.deadline

    def remaining_at(self, now: float) -> int:
        if not self.active:
            return 0
        return max(0, int(round((self.deadline - now) * 1000.0)))

    def progress_at(self, now: float) -> float:
        if self.total_ms <= 0:
            return 0.0
        return max(0.0, min(1.0, self.remaining_at(now) / float(self.total_ms)))


@dataclass(slots=True)
class Scene:
    timestamp: float
    layers: list[LayerVisual] = field(default_factory=list)
    main_layer_valid: bool = True
    diagnostics: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Frame:
    leds: list[Color]
    timestamp: float


@dataclass(slots=True)
class PresetManifest:
    preset_id: str
    name: str
    description: str
    command: str
    target_layer: str = "active_visual"
    supports_cli: bool = True
    supports_api: bool = True
    sample_spec: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PresetBuildResult:
    preset_id: str
    mode: str
    payload: dict[str, Any]
    visual: Visual
    state_visual: Visual | None = None
    state_mode: str = "custom"
    valid: bool = True


@dataclass(slots=True)
class DiscoveredPreset:
    manifest: PresetManifest
    folder: Path
    module_path: Path
    sample_path: Path | None
    build_preset: Callable[[dict[str, Any]], PresetBuildResult]
