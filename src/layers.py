from __future__ import annotations

from dataclasses import dataclass, field

from .models import ActiveVisualState, BaseState, CountdownState, Event, LayerVisual, StateLayerState


STATE_LAYER_PRIORITY = 100
MAIN_LAYER_PRIORITY = 200
DIRECTION_LAYER_PRIORITY = 250
COUNTDOWN_LAYER_PRIORITY = 275
EVENT_LAYER_PRIORITY = 300


@dataclass(slots=True)
class EventQueue:
    pending_events: list[Event] = field(default_factory=list)
    current_event: Event | None = None

    def enqueue(self, event: Event) -> None:
        self.pending_events.append(event)

    def clear(self) -> None:
        self.pending_events.clear()
        self.current_event = None

    def _discard_expired_pending(self, now: float) -> None:
        self.pending_events = [event for event in self.pending_events if not event.is_expired(now)]

    def _pick_next(self) -> Event | None:
        if not self.pending_events:
            return None
        best_index = min(
            range(len(self.pending_events)),
            key=lambda idx: (-self.pending_events[idx].priority, self.pending_events[idx].created_at),
        )
        return self.pending_events.pop(best_index)

    def _peek_next(self) -> Event | None:
        if not self.pending_events:
            return None
        return min(
            self.pending_events,
            key=lambda event: (-event.priority, event.created_at),
        )

    def active_layer_visuals(self, now: float) -> list[LayerVisual]:
        self._discard_expired_pending(now)

        if self.current_event and self.current_event.is_expired(now):
            self.current_event = None

        contender = self._peek_next()
        if self.current_event is not None and contender is not None and contender.priority > self.current_event.priority:
            self.pending_events.append(self.current_event)
            self.current_event = None

        if self.current_event is None:
            self.current_event = self._pick_next()

        if self.current_event is None:
            return []

        return [
            LayerVisual(
                name=f"event:{self.current_event.id}",
                priority=EVENT_LAYER_PRIORITY,
                visual=self.current_event.visual,
            )
        ]


@dataclass(slots=True)
class LayerStore:
    base_state: BaseState = field(default_factory=BaseState)
    state_layer: StateLayerState = field(default_factory=StateLayerState)
    main_layer: ActiveVisualState | None = None
    direction_deg: float | None = None
    direction_visual: object | None = None
    countdown: CountdownState | None = None
    countdown_visual: object | None = None
    brightness: float = 1.0
    enabled: bool = True
    event_layer: EventQueue = field(default_factory=EventQueue)
