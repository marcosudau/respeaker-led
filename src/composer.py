from __future__ import annotations

from .effect_registry import EffectRegistry, build_default_effect_registry
from .effect_schema import LayerId, RenderContext
from .effects import dynamic_frame
from .layers import LayerEntry, LayerStore
from .models import LED_COUNT, LayerVisual, Scene


def _public_params(params: dict) -> dict:
    return {key: value for key, value in params.items() if not str(key).startswith("__")}


class SceneComposer:
    def __init__(self, effect_registry: EffectRegistry | None = None) -> None:
        self.effect_registry = effect_registry or build_default_effect_registry()

    def compose(self, store: LayerStore, now: float) -> Scene:
        layers: list[LayerVisual] = []
        diagnostics: list[str] = []
        main_layer_valid = store.layer(LayerId.MAIN_LAYER).valid

        for layer_id in sorted(LayerId, key=lambda item: store.layer(item).state.priority):
            entry = store.layer(layer_id)
            invocation = entry.state.active_invocation
            if not entry.state.enabled or invocation is None:
                continue
            layers.append(
                LayerVisual(
                    name=self._layer_name(layer_id, entry, invocation),
                    priority=entry.state.priority,
                    visual=dynamic_frame(
                        lambda current_now, inv=invocation, current_layer=layer_id: self._render_invocation(inv, current_layer, current_now),
                        exclusive=False,
                    ),
                )
            )

        if not main_layer_valid:
            diagnostics.append("active-visual-invalid")

        return Scene(timestamp=now, layers=layers, main_layer_valid=main_layer_valid, diagnostics=diagnostics)

    def _layer_name(self, layer_id: LayerId, entry: LayerEntry, invocation) -> str:
        scene_name = invocation.params.get("__scene_name")
        if scene_name:
            return str(scene_name)
        if layer_id is LayerId.EVENT_LAYER:
            return f"event:{invocation.invocation_id}"
        if layer_id is LayerId.MAIN_LAYER:
            item_id = entry.item_id or invocation.invocation_id
            return f"active_visual:{item_id}"
        return entry.scene_name

    def _render_invocation(self, invocation, layer_id: LayerId, now: float) -> list[int | None]:
        registered = self.effect_registry.get(invocation.effect_id)
        effect = registered.effect_class()
        return effect.render(
            RenderContext(
                now=now,
                led_count=LED_COUNT,
                layer_id=layer_id,
                definition=registered.definition,
                invocation=invocation,
                params=_public_params(invocation.params),
            )
        )
