from __future__ import annotations

from src.engine.composer import SceneComposer
from src.engine.effect_registry import build_default_effect_registry
from src.core.effect_schema import (
    BaseEffect,
    CommandKind,
    CompositionMode,
    DefinitionType,
    EffectCapabilities,
    EffectDefinition,
    EffectInvocation,
    EffectParamDefinition,
    InputContext,
    InputMode,
    InputSamplingPolicy,
    LayerId,
    LayerRule,
    NormalizedCommand,
    OverlayMode,
    PlaybackMode,
    RenderContext,
)
from src.core.layers import LayerStore
from src.integrations.application_commands import build_effect_invocation


class PullOverlayEffect(BaseEffect):
    definition = EffectDefinition(
        id="pull_overlay",
        title="Pull Overlay",
        description="Pull sampling test definition",
        definition_type=DefinitionType.OVERLAY,
        overlay_mode=OverlayMode.CONTROLLED,
        runtime_input_schema={
            "sample": EffectParamDefinition(
                name="sample",
                type="int",
                required=True,
            ),
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.PERSISTENT,),
            supports_transparency=True,
        ),
        layer_rules={
            LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.PERSISTENT,),
                requires_indefinite_duration=True,
                allows_transparency=True,
            ),
        },
        composition=CompositionMode.TRANSPARENT,
        input_sampling=InputSamplingPolicy(
            mode=InputMode.PULL,
            interval_ms=1000,
            heartbeat_interval_ms=1000,
            max_missed_heartbeats=3,
        ),
    )

    def __init__(self) -> None:
        self.samples = 0

    def sample_inputs(self, ctx: InputContext) -> dict | None:
        del ctx
        self.samples += 1
        return {"sample": 7} if self.samples == 1 else None

    def render(self, ctx: RenderContext) -> list[int | None]:
        return [ctx.inputs.get("sample")] * ctx.led_count


def make_invocation(
    effect_id: str,
    layer_id: LayerId,
    *,
    invocation_id: str,
    created_at: float,
    priority: int | None = None,
    duration_ms: int | None = None,
    params: dict | None = None,
    inputs: dict | None = None,
):
    registry = build_default_effect_registry()
    command_params = dict(params or {})
    if duration_ms is not None:
        command_params["duration_ms"] = duration_ms
    return build_effect_invocation(
        NormalizedCommand(
            kind=CommandKind.SET_EFFECT,
            target_layer=layer_id,
            effect_id=effect_id,
            params=command_params,
            inputs=dict(inputs or {}),
            priority=priority,
            timestamp=created_at,
            enqueue=layer_id is LayerId.EVENT_LAYER,
            replace_existing=layer_id is not LayerId.EVENT_LAYER,
        ),
        registry,
        invocation_id=invocation_id,
        created_at=created_at,
    )


def test_composer_orders_state_active_direction_countdown_and_event_layers():
    store = LayerStore()
    registry = build_default_effect_registry()
    store.set_invocation(
        LayerId.BACKGROUND_STATE_LAYER,
        make_invocation("solid_color", LayerId.BACKGROUND_STATE_LAYER, invocation_id="idle-bg", created_at=0.0, params={"color": 0x010101}),
        scene_name="state_layer",
        item_id="idle",
        mode="idle",
    )
    store.set_invocation(
        LayerId.STATE_LAYER,
        make_invocation("solid_color", LayerId.STATE_LAYER, invocation_id="primary", created_at=0.0, params={"color": 0x112233}),
        scene_name="state:primary",
        item_id="download",
        mode="manual",
    )
    store.set_invocation(
        LayerId.ONGOING_OVERLAY_LAYER,
        make_invocation("direction_indicator", LayerId.ONGOING_OVERLAY_LAYER, invocation_id="direction", created_at=0.0, inputs={"direction": 120.0}),
        scene_name="direction_overlay",
        item_id="direction-overlay",
        mode="direction",
    )
    store.set_invocation(
        LayerId.TEMP_OVERLAY_LAYER,
        make_invocation(
            "countdown_circle",
            LayerId.TEMP_OVERLAY_LAYER,
            invocation_id="countdown",
            created_at=0.0,
            duration_ms=2000,
            params={"total_ms": 4000, "deadline_ts": 2.0},
        ),
        scene_name="countdown_overlay",
        item_id="countdown-overlay",
        mode="countdown",
    )
    store.set_invocation(
        LayerId.EVENT_LAYER,
        make_invocation(
            "warning_flash",
            LayerId.EVENT_LAYER,
            invocation_id="warning",
            created_at=0.0,
            priority=500,
            duration_ms=2000,
            params={"color": 0xFF0000, "background_color": 0x120400, "period_ms": 800, "duty_cycle": 0.5, "__scene_name": "event:warning"},
        ),
        enqueue=True,
    )

    scene = SceneComposer(registry).compose(store, now=0.5)

    assert [layer.name for layer in scene.layers] == [
        "state_layer",
        "state:primary",
        "countdown_overlay",
        "direction_overlay",
        "event:warning",
    ]


def test_event_queue_keeps_running_event_until_it_expires_and_then_uses_priority_fifo():
    store = LayerStore()
    registry = build_default_effect_registry()
    store.set_invocation(
        LayerId.EVENT_LAYER,
        make_invocation(
            "warning_flash",
            LayerId.EVENT_LAYER,
            invocation_id="first",
            created_at=0.0,
            priority=10,
            duration_ms=3000,
            params={"color": 0x111111, "background_color": 0x010101, "period_ms": 400, "duty_cycle": 0.5, "__scene_name": "event:first"},
        ),
        enqueue=True,
    )
    store.set_invocation(
        LayerId.EVENT_LAYER,
        make_invocation(
            "warning_flash",
            LayerId.EVENT_LAYER,
            invocation_id="second",
            created_at=0.6,
            priority=999,
            duration_ms=1000,
            params={"color": 0x222222, "background_color": 0x020202, "period_ms": 400, "duty_cycle": 0.5, "__scene_name": "event:second"},
        ),
        enqueue=True,
    )
    store.advance(0.7)
    first_scene = SceneComposer(registry).compose(store, now=0.7)
    store.advance(3.1)
    second_scene = SceneComposer(registry).compose(store, now=3.1)

    assert first_scene.layers[-1].name == "event:first"
    assert second_scene.layers[-1].name == "event:second"


def test_pull_overlay_samples_on_interval_and_expires_after_missed_heartbeats():
    registry = build_default_effect_registry()
    registry.register(PullOverlayEffect, source_id="tests")
    invocation = EffectInvocation(
        invocation_id="pull-1",
        effect_id="pull_overlay",
        target_layer=LayerId.ONGOING_OVERLAY_LAYER,
        playback_mode=PlaybackMode.PERSISTENT,
        created_at=0.0,
    )
    store = LayerStore()
    store.set_invocation(
        LayerId.ONGOING_OVERLAY_LAYER,
        invocation,
        scene_name="pull_overlay",
        item_id="pull-1",
        mode="test",
    )
    composer = SceneComposer(registry)
    scene = composer.compose(store, now=0.0)
    provider = scene.layers[0].visual.params["provider"]

    assert provider(0.0) == [7] * 12
    assert provider(0.5) == [7] * 12
    assert provider(1.0) == [7] * 12
    assert provider(2.999) == [7] * 12
    assert provider(3.0) == [None] * 12
    assert invocation.input_error == "input source returned no value"
