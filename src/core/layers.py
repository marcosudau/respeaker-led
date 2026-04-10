from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .effect_schema import DEFAULT_LAYER_PRIORITIES, EffectInvocation, LayerId, LayerState
from .models import BaseState, CountdownState


LEGACY_SCENE_NAMES: dict[LayerId, str] = {
    LayerId.BACKGROUND_STATE_LAYER: "state_layer",
    LayerId.STATE_LAYER: "state_overlay",
    LayerId.MAIN_LAYER: "active_visual",
    LayerId.TEMP_OVERLAY_LAYER: "temp_overlay",
    LayerId.ONGOING_OVERLAY_LAYER: "ongoing_overlay",
    LayerId.EVENT_LAYER: "event",
}


@dataclass(slots=True)
class LayerEntry:
    state: LayerState
    scene_name: str
    item_id: str | None = None
    mode: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    valid: bool = True

    def reset(self) -> None:
        self.state.active_invocation = None
        self.state.queue.clear()
        self.item_id = None
        self.mode = None
        self.payload = {}
        self.valid = True


def _default_entries() -> dict[LayerId, LayerEntry]:
    return {
        layer_id: LayerEntry(
            state=LayerState(layer_id=layer_id, priority=DEFAULT_LAYER_PRIORITIES[layer_id]),
            scene_name=LEGACY_SCENE_NAMES[layer_id],
        )
        for layer_id in LayerId
    }


def _is_expired(invocation: EffectInvocation, now: float) -> bool:
    if invocation.requested_duration_ms is None:
        return False
    activated_at = invocation.params.get("__activated_at", invocation.created_at)
    return now >= float(activated_at) + (invocation.requested_duration_ms / 1000.0)


def _event_sort_key(invocation: EffectInvocation) -> tuple[int, float]:
    return (-invocation.effective_priority(), invocation.created_at)


@dataclass(slots=True)
class LayerStore:
    base_state: BaseState = field(default_factory=BaseState)
    countdown: CountdownState | None = None
    direction_deg: float | None = None
    brightness: float = 1.0
    enabled: bool = True
    layers: dict[LayerId, LayerEntry] = field(default_factory=_default_entries)

    def layer(self, layer_id: LayerId) -> LayerEntry:
        return self.layers[layer_id]

    @property
    def current_event(self) -> EffectInvocation | None:
        return self.layer(LayerId.EVENT_LAYER).state.active_invocation

    @property
    def pending_events(self) -> list[EffectInvocation]:
        return list(self.layer(LayerId.EVENT_LAYER).state.queue)

    def clear_layer(self, layer_id: LayerId) -> list[str]:
        entry = self.layer(layer_id)
        removed_ids: list[str] = []
        if entry.state.active_invocation is not None:
            removed_ids.append(entry.state.active_invocation.invocation_id)
        removed_ids.extend(invocation.invocation_id for invocation in entry.state.queue)
        entry.reset()
        entry.scene_name = LEGACY_SCENE_NAMES[layer_id]
        entry.state.enabled = True
        return removed_ids

    def set_invocation(
        self,
        layer_id: LayerId,
        invocation: EffectInvocation,
        *,
        scene_name: str | None = None,
        item_id: str | None = None,
        mode: str | None = None,
        payload: dict[str, Any] | None = None,
        valid: bool = True,
        enqueue: bool = False,
    ) -> list[str]:
        entry = self.layer(layer_id)
        if layer_id is LayerId.EVENT_LAYER and enqueue:
            self._insert_event(entry.state.queue, invocation)
            if entry.state.active_invocation is None:
                entry.state.active_invocation = entry.state.queue.pop(0)
                entry.state.active_invocation.params.setdefault("__activated_at", invocation.created_at)
            return []

        removed_ids = self.clear_layer(layer_id)
        entry.state.active_invocation = invocation
        entry.scene_name = scene_name or LEGACY_SCENE_NAMES[layer_id]
        entry.item_id = item_id
        entry.mode = mode
        entry.payload = dict(payload or {})
        entry.valid = valid
        return removed_ids

    def advance(self, now: float) -> list[str]:
        expired_ids: list[str] = []

        for layer_id, entry in self.layers.items():
            if layer_id is LayerId.EVENT_LAYER:
                expired_ids.extend(self._advance_event_layer(entry, now))
                continue

            active = entry.state.active_invocation
            if active is None or not _is_expired(active, now):
                continue
            expired_ids.append(active.invocation_id)
            entry.reset()
            entry.scene_name = LEGACY_SCENE_NAMES[layer_id]
            entry.state.enabled = True

        return expired_ids

    def _advance_event_layer(self, entry: LayerEntry, now: float) -> list[str]:
        expired_ids: list[str] = []
        active = entry.state.active_invocation
        if active is not None and _is_expired(active, now):
            expired_ids.append(active.invocation_id)
            entry.state.active_invocation = None
        if entry.state.active_invocation is None and entry.state.queue:
            entry.state.active_invocation = entry.state.queue.pop(0)
            entry.state.active_invocation.params["__activated_at"] = now
        return expired_ids

    def _insert_event(self, queue: list[EffectInvocation], invocation: EffectInvocation) -> None:
        insert_at = len(queue)
        candidate_key = _event_sort_key(invocation)
        for index, queued in enumerate(queue):
            if candidate_key < _event_sort_key(queued):
                insert_at = index
                break
        queue.insert(insert_at, invocation)
