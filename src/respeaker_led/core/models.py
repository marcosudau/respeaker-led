from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


LED_COUNT = 12
Color = int

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

