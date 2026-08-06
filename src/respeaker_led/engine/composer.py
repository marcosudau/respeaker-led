from __future__ import annotations

import logging
from collections.abc import Callable, Mapping

from .effect_registry import EffectRegistry, build_default_effect_registry
from ..core.effect_schema import InputContext, InputMode, LayerId, RenderContext
from ..core.layers import LayerEntry, LayerStore
from ..core.models import LED_COUNT, LayerVisual, Scene, Visual
from ..core.parameter_validation import normalize_runtime_inputs


logger = logging.getLogger("led_controller.composer")


def _public_params(params: dict) -> dict:
    return {key: value for key, value in params.items() if not str(key).startswith("__")}


class SceneComposer:
    def __init__(
        self,
        effect_registry: EffectRegistry | None = None,
        input_providers: Mapping[str, Callable[[InputContext], dict | None]] | None = None,
    ) -> None:
        self.effect_registry = effect_registry or build_default_effect_registry()
        self._input_providers = dict(input_providers or {})
        self._effect_instances: dict[str, object] = {}

    def compose(self, store: LayerStore, now: float) -> Scene:
        layers: list[LayerVisual] = []
        diagnostics: list[str] = []
        main_layer_valid = True
        active_invocation_ids: set[str] = set()

        for layer_id in sorted(LayerId, key=lambda item: store.layer(item).state.priority):
            entry = store.layer(layer_id)
            invocation = entry.state.active_invocation
            if not entry.state.enabled or invocation is None:
                continue
            active_invocation_ids.add(invocation.invocation_id)
            layers.append(
                LayerVisual(
                    name=self._layer_name(layer_id, entry, invocation),
                    priority=entry.state.priority,
                    visual=Visual(
                        "dynamic_frame",
                        {
                            "provider": lambda current_now, inv=invocation, current_layer=layer_id: self._render_invocation(
                                inv,
                                current_layer,
                                current_now,
                            )
                        },
                        exclusive=False,
                    ),
                )
            )

        if not main_layer_valid:
            diagnostics.append("active-visual-invalid")

        self._effect_instances = {
            invocation_id: instance
            for invocation_id, instance in self._effect_instances.items()
            if invocation_id in active_invocation_ids
        }
        return Scene(timestamp=now, layers=layers, main_layer_valid=main_layer_valid, diagnostics=diagnostics)

    def _layer_name(self, layer_id: LayerId, entry: LayerEntry, invocation) -> str:
        scene_name = invocation.params.get("__scene_name")
        if scene_name:
            return str(scene_name)
        if layer_id is LayerId.EVENT_LAYER:
            return f"event:{invocation.invocation_id}"
        return entry.scene_name

    def _render_invocation(self, invocation, layer_id: LayerId, now: float) -> list[int | None]:
        registered = self.effect_registry.get(invocation.effect_id)
        effect = self._effect_instances.get(invocation.invocation_id)
        if effect is None or not isinstance(effect, registered.effect_class):
            effect = registered.effect_class()
            self._effect_instances[invocation.invocation_id] = effect
        self._sample_inputs(effect, registered.definition, invocation, now)
        return effect.render(
            RenderContext(
                now=now,
                led_count=LED_COUNT,
                layer_id=layer_id,
                definition=registered.definition,
                invocation=invocation,
                params=_public_params(invocation.params),
                inputs=self._effective_inputs(registered.definition, invocation, now),
            )
        )

    def _sample_inputs(self, effect, definition, invocation, now: float) -> None:
        policy = definition.effective_input_sampling()
        if policy is None or policy.mode is not InputMode.PULL:
            return
        if invocation.input_last_attempt_at is not None:
            elapsed_ms = (now - invocation.input_last_attempt_at) * 1000.0
            if elapsed_ms < policy.interval_ms:
                return

        invocation.input_last_attempt_at = now
        try:
            input_context = InputContext(
                now=now,
                led_count=LED_COUNT,
                config=_public_params(invocation.params),
                previous_inputs=dict(invocation.inputs),
            )
            if policy.provider_id is None:
                sampled = effect.sample_inputs(input_context)
            else:
                provider = self._input_providers.get(policy.provider_id)
                if provider is None:
                    raise RuntimeError(
                        f"input provider {policy.provider_id!r} is not available"
                    )
                sampled = provider(input_context)
            if sampled is None:
                invocation.input_error = "input source returned no value"
                return
            normalized = normalize_runtime_inputs(
                definition,
                sampled,
                require_required=True,
            )
        except Exception as exc:
            invocation.input_error = str(exc)
            logger.warning(
                "input sampling failed effect=%s invocation=%s error=%s",
                definition.id,
                invocation.invocation_id,
                exc,
            )
            return

        invocation.inputs.update(normalized)
        invocation.input_last_success_at = now
        invocation.input_error = None

    def _effective_inputs(self, definition, invocation, now: float) -> dict:
        values = dict(invocation.inputs)
        policy = definition.effective_input_sampling()
        if policy is None:
            return values
        last_success = invocation.input_last_success_at
        heartbeat_anchor = invocation.created_at if last_success is None else last_success
        if (now - heartbeat_anchor) * 1000.0 < policy.failure_after_ms:
            return values
        for name in definition.runtime_input_schema:
            values[name] = None
        return values
