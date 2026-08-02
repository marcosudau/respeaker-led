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


def _event_rules() -> dict[LayerId, LayerRule]:
    return {
        LayerId.EVENT_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
            requires_finite_duration=True,
            queue_mode=QueueMode.PRIORITY_FIFO,
        )
    }


def _brightness_param() -> EffectParamDefinition:
    return EffectParamDefinition(name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0)


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


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _event_duration_ms(ctx: RenderContext, params: dict[str, Any], default_ms: int) -> int:
    requested = ctx.invocation.requested_duration_ms
    if requested is None:
        requested = _parse_int(params.get("duration_ms"), default_ms)
    return max(1, int(requested))


def _flash_active_at_elapsed(ctx: RenderContext, params: dict[str, Any], count: int, default_duration_ms: int) -> bool:
    duration_ms = _event_duration_ms(ctx, params, default_duration_ms)
    pause_ms = max(0, _parse_int(params.get("pause_ms"), 0))
    flash_ms = max(1, int((duration_ms - (pause_ms * max(0, count - 1))) / float(max(1, count))))
    elapsed_ms = max(0, int(round((ctx.now - ctx.invocation.created_at) * 1000.0)))
    for burst_index in range(count):
        start_ms = burst_index * (flash_ms + pause_ms)
        if start_ms <= elapsed_ms < start_ms + flash_ms:
            return True
    return False


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="triple_flash",
        definition_type=DefinitionType.EVENT,
        title="Triple Flash",
        description="Dreifaches Aufblitzen mit Dauer und Pause.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#FFFFFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=700, minimum=1, unit="ms"),
            "pause_ms": EffectParamDefinition(name="pause_ms", type="duration_ms", default=120, minimum=0, unit="ms"),
        },
        defaults={"color": "#FFFFFF", "background_color": "#000000", "brightness": 1.0, "duration_ms": 700, "pause_ms": 120},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
        ),
        layer_rules=_event_rules(),
        color_model=ColorModel.MONO,
        composition=CompositionMode.OPAQUE,
        animated=False,
        directional=False,
        tags=("builtin", "event", "flash"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame_color = _color_param(params, "color", 0xFFFFFF) if _flash_active_at_elapsed(ctx, params, 3, 700) else _background_color(params)
        return [frame_color] * ctx.led_count
