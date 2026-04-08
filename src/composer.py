from __future__ import annotations

from .layers import COUNTDOWN_LAYER_PRIORITY, DIRECTION_LAYER_PRIORITY, LayerStore, MAIN_LAYER_PRIORITY, STATE_LAYER_PRIORITY
from .models import LayerVisual, Scene


class SceneComposer:
    def compose(self, store: LayerStore, now: float) -> Scene:
        layers: list[LayerVisual] = []
        diagnostics: list[str] = []

        if store.state_layer.enabled and store.state_layer.visual is not None:
            layers.append(LayerVisual(name="state_layer", priority=STATE_LAYER_PRIORITY, visual=store.state_layer.visual))

        main_layer_valid = True
        if store.main_layer is not None:
            main_layer_valid = store.main_layer.valid
            if store.main_layer.visual is not None:
                layers.append(
                    LayerVisual(
                        name=f"active_visual:{store.main_layer.id}",
                        priority=MAIN_LAYER_PRIORITY,
                        visual=store.main_layer.visual,
                    )
                )
            if not main_layer_valid:
                diagnostics.append("active-visual-invalid")

        if store.direction_visual is not None:
            layers.append(LayerVisual(name="direction_overlay", priority=DIRECTION_LAYER_PRIORITY, visual=store.direction_visual))

        if store.countdown_visual is not None:
            layers.append(LayerVisual(name="countdown_overlay", priority=COUNTDOWN_LAYER_PRIORITY, visual=store.countdown_visual))

        layers.extend(store.event_layer.active_layer_visuals(now))
        layers.sort(key=lambda item: item.priority)
        return Scene(timestamp=now, layers=layers, main_layer_valid=main_layer_valid, diagnostics=diagnostics)
