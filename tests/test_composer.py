from __future__ import annotations

from src.effects import solid
from src.composer import SceneComposer
from src.layers import EventQueue, LayerStore
from src.models import Event, MainLayerState, StateLayerState


def test_composer_orders_state_active_direction_countdown_and_event_layers():
    store = LayerStore()
    store.state_layer = StateLayerState(mode="idle", visual=solid(0x010101))
    store.main_layer = MainLayerState(id="download", mode="manual", visual=solid(0x112233))
    store.direction_visual = solid(0x224466)
    store.countdown_visual = solid(0xFFAA00)
    store.event_layer.enqueue(
        Event(
            id="warning",
            name="warning",
            visual=solid(0xFF0000, exclusive=True),
            priority=500,
            created_at=0.0,
            duration=2.0,
            exclusive=True,
        )
    )

    scene = SceneComposer().compose(store, now=0.5)

    assert [layer.name for layer in scene.layers] == [
        "state_layer",
        "active_visual:download",
        "direction_overlay",
        "countdown_overlay",
        "event:warning",
    ]


def test_event_queue_preempts_lower_priority_and_restores_it_after_higher_priority_expires():
    queue = EventQueue()
    queue.enqueue(
        Event(
            id="first",
            name="info",
            visual=solid(0x111111, exclusive=True),
            priority=10,
            created_at=0.0,
            duration=3.0,
            exclusive=True,
        )
    )

    first = queue.active_layer_visuals(now=0.5)

    queue.enqueue(
        Event(
            id="second",
            name="critical",
            visual=solid(0x222222, exclusive=True),
            priority=999,
            created_at=0.6,
            duration=1.0,
            exclusive=True,
        )
    )

    second = queue.active_layer_visuals(now=0.7)
    third = queue.active_layer_visuals(now=1.7)

    assert first[0].name == "event:first"
    assert second[0].name == "event:second"
    assert third[0].name == "event:first"
