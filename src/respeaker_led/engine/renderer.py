from __future__ import annotations

from typing import Iterable

from ..core.models import Color, Frame, LED_COUNT, Scene, Visual


def render_visual_to_pixels(visual: Visual, now: float) -> list[Color | None]:
    visual_type = visual.type
    params = visual.params

    if visual_type == "dynamic_frame":
        provider = params["provider"]
        colors = provider(now)
        if len(colors) != LED_COUNT:
            raise ValueError(f"dynamic_frame expects {LED_COUNT} colors")
        return [int(color) if color is not None else None for color in colors]

    raise ValueError(f"Unsupported visual type: {visual_type}")


class SceneRenderer:
    def render(self, scene: Scene) -> Frame:
        frame = [0] * LED_COUNT
        for layer in self._ordered_layers(scene):
            pixels = self._render_visual(layer.visual, scene.timestamp)
            frame = self._overlay(frame, pixels, layer.visual.exclusive)

        if not scene.main_layer_valid:
            diagnostics = self._render_visual(
                Visual(
                    "dynamic_frame",
                    {"provider": lambda now: [0xFFFFFF if idx == 0 and int(now * 2) % 4 < 2 else None for idx in range(LED_COUNT)]},
                    exclusive=False,
                ),
                scene.timestamp,
            )
            frame = self._overlay(frame, diagnostics, False)

        return Frame(leds=frame, timestamp=scene.timestamp)

    def _ordered_layers(self, scene: Scene) -> Iterable:
        return scene.layers

    def _overlay(self, base: list[Color], top: list[Color | None], exclusive: bool) -> list[Color]:
        result = [0] * LED_COUNT if exclusive else list(base)
        for index, color in enumerate(top):
            if color is not None:
                result[index] = color
        return result

    def _render_visual(self, visual: Visual, now: float) -> list[Color | None]:
        return render_visual_to_pixels(visual, now)
