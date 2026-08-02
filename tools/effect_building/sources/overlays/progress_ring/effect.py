from __future__ import annotations

import hashlib
import math
from typing import Any

from src.core.color_math import blend, scale_color
from src.core.effect_schema import (
    BaseEffect,
    ColorModel,
    CompositionMode,
    InputSamplingPolicy,
    DefinitionType,
    EffectCapabilities,
    EffectDefinition,
    EffectParamDefinition,
    LayerId,
    LayerRule,
    OverlayMode,
    PlaybackMode,
    QueueMode,
    RenderContext,
)


def _merge_params(ctx: RenderContext) -> dict[str, Any]:
    params = dict(ctx.definition.defaults)
    params.update(ctx.params)
    params.update(ctx.inputs)
    return params


def _parse_color(value: Any, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value

    text = str(value).strip()
    if not text:
        return default
    if text.startswith("#"):
        return int(text[1:], 16)
    if text.lower().startswith("0x"):
        return int(text, 16)
    return int(text, 16)


def _parse_float(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _overlay_rules() -> dict[LayerId, LayerRule]:
    return {
        LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            requires_indefinite_duration=True,
            allows_transparency=True,
        ),
    }


def _brightness_param() -> EffectParamDefinition:
    return EffectParamDefinition(name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0)


def _reverse_param() -> EffectParamDefinition:
    return EffectParamDefinition(name="reverse", type="bool", default=False)


def _raw_color_param(
    params: dict[str, Any],
    key: str,
    default: int,
    *aliases: str,
) -> int:
    for candidate in (key, *aliases):
        if candidate in params:
            return _parse_color(params.get(candidate), default)
    return default


def _brightness(params: dict[str, Any], default: float = 1.0) -> float:
    return _clamp01(_parse_float(params.get("brightness"), default))


def _color_param(
    params: dict[str, Any],
    key: str,
    default: int,
    *aliases: str,
) -> int:
    color = _raw_color_param(params, key, default, *aliases)
    brightness = _brightness(params, 1.0)
    return color if brightness >= 1.0 else scale_color(color, brightness)


def _background_color(params: dict[str, Any], default: int = 0x000000) -> int:
    return _raw_color_param(params, "background_color", default, "base_color")


def _parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _step_sign(params: dict[str, Any], default_reverse: bool = False) -> int:
    return -1 if _parse_bool(params.get("reverse"), default_reverse) else 1


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _wrap_index(index: int, led_count: int) -> int:
    return index % max(1, led_count)


def _segment_indices(start: int, length: int, led_count: int, *, step_sign: int = 1) -> list[int]:
    safe_length = max(0, min(int(length), led_count))
    return [_wrap_index(start + (offset * step_sign), led_count) for offset in range(safe_length)]


def _paint_segment(
    frame: list[int | None],
    start: int,
    length: int,
    color: int | list[int],
    *,
    step_sign: int = 1,
) -> None:
    indices = _segment_indices(start, length, len(frame), step_sign=step_sign)
    if isinstance(color, list):
        for index, led_index in enumerate(indices):
            frame[led_index] = color[min(index, len(color) - 1)]
        return
    for led_index in indices:
        frame[led_index] = color


def _normalized_level(value: Any, default: float) -> float:
    numeric = _parse_float(value, default)
    if numeric > 1.0:
        numeric /= 100.0
    return _clamp01(numeric)


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="progress_ring",
        definition_type=DefinitionType.OVERLAY,
        overlay_mode=OverlayMode.CONTROLLED,
        title="Progress Ring",
        description="Ringfoermiger Fortschritt mit Richtung und Start-LED.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "reverse": _reverse_param(),
            "start_led": EffectParamDefinition(name="start_led", type="int", default=0, minimum=0),
        },
        runtime_input_schema={
            "progress": EffectParamDefinition(
                name="progress",
                type="float",
                default=0.0,
                minimum=0.0,
                maximum=100.0,
                aliases=("progress_value", "value"),
            ),
        },
        defaults={
            "color": "#33AAFF",
            "background_color": "#000000",
            "brightness": 1.0,
            "reverse": False,
            "start_led": 0,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_transparency=True,
            restorable=True,
        ),
        layer_rules=_overlay_rules(),
        color_model=ColorModel.MONO,
        composition=CompositionMode.TRANSPARENT,
        animated=False,
        directional=True,
        input_sampling=InputSamplingPolicy(),
        tags=("builtin", "overlay", "progress"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        ratio = _normalized_level(params.get("progress"), 0.0)
        count = int(round(ratio * ctx.led_count))
        frame = [_background_color(params)] * ctx.led_count
        _paint_segment(
            frame,
            _parse_int(params.get("start_led"), 0),
            count,
            _color_param(params, "color", 0x33AAFF),
            step_sign=_step_sign(params),
        )
        return frame
