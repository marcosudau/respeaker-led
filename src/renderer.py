from __future__ import annotations

import math
from typing import Iterable

from .color_math import blend
from .models import Color, Frame, LED_COUNT, Scene, Visual


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
        visual_type = visual.type
        params = visual.params

        if visual_type == "solid":
            return [int(params["color"])] * LED_COUNT

        if visual_type == "pulse":
            period = max(0.1, float(params.get("period", 2.0)))
            base_color = int(params.get("base_color", 0))
            color = int(params["color"])
            phase = (math.sin((now / period) * 2.0 * math.pi) + 1.0) / 2.0
            factor = 0.15 + phase * 0.85
            return [blend(base_color, color, factor) for _ in range(LED_COUNT)]

        if visual_type == "blink":
            period = max(0.1, float(params.get("period", 1.0)))
            duty_cycle = max(0.01, min(0.99, float(params.get("duty_cycle", 0.5))))
            base_color = int(params.get("base_color", 0))
            color = int(params["color"])
            phase = (now % period) / period
            current = color if phase < duty_cycle else base_color
            return [current] * LED_COUNT

        if visual_type == "progress":
            value = max(0.0, min(100.0, float(params.get("value", 0.0))))
            active = int(round((value / 100.0) * LED_COUNT))
            color = int(params["color"])
            base_color = int(params.get("base_color", 0))
            return [color if index < active else base_color for index in range(LED_COUNT)]

        if visual_type == "segments":
            leds: list[Color | None] = [None] * LED_COUNT
            for segment in params.get("segments", []):
                start = int(segment.get("start", 0))
                end = int(segment.get("end", start))
                color = int(segment.get("color", 0))
                for index in range(max(0, start), min(LED_COUNT - 1, end) + 1):
                    leds[index] = color
            return leds

        if visual_type == "ring_frame":
            colors = list(params.get("colors", []))
            if len(colors) != LED_COUNT:
                raise ValueError(f"ring_frame expects {LED_COUNT} colors")
            return [int(color) if color is not None else None for color in colors]

        if visual_type == "dynamic_frame":
            provider = params["provider"]
            colors = provider(now)
            if len(colors) != LED_COUNT:
                raise ValueError(f"dynamic_frame expects {LED_COUNT} colors")
            return [int(color) if color is not None else None for color in colors]

        raise ValueError(f"Unsupported visual type: {visual_type}")
