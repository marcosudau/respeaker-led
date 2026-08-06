from __future__ import annotations

import hashlib
import math
from typing import Any

from respeaker_led.core.color_math import blend, scale_color
from respeaker_led.core.effect_schema import (
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


def _persistent_state_rules() -> dict[LayerId, LayerRule]:
    return {
        LayerId.BACKGROUND_STATE_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            requires_indefinite_duration=True,
            persistent_storage=True,
        ),
        LayerId.STATE_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            requires_indefinite_duration=True,
        ),
    }


def _state_rules() -> dict[LayerId, LayerRule]:
    return _persistent_state_rules()


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


def _speed(params: dict[str, Any], default: float) -> float:
    return default * max(0.1, _parse_float(params.get("speed"), 1.0))


def _wrap_index(index: int, led_count: int) -> int:
    return index % max(1, led_count)


def _moving_head(now: float, speed: float, led_count: int, *, step_sign: int = 1, offset: int = 0) -> int:
    if led_count <= 0:
        return 0
    return _wrap_index(offset + int(math.floor(now * speed * step_sign)), led_count)


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="chase_dot",
        definition_type=DefinitionType.STATE,
        title="Chase Dot",
        description="Ein einzelner Laufpunkt mit konfigurierbarer Richtung und Geschwindigkeit.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=1.0, minimum=0.1, maximum=10.0, unit="multiplier"),
            "color": EffectParamDefinition(name="color", type="color", default="#FFFFFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "reverse": _reverse_param(),
        },
        defaults={"speed": 6.0, "color": "#FFFFFF", "background_color": "#000000", "brightness": 1.0, "reverse": False},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        color_model=ColorModel.MONO,
        composition=CompositionMode.OPAQUE,
        animated=True,
        directional=True,
        tags=("builtin", "state", "animated", "dot"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame = [_background_color(params)] * ctx.led_count
        head = _moving_head(
            ctx.now,
            _speed(params, 6.0),
            ctx.led_count,
            step_sign=_step_sign(params),
        )
        frame[head] = _color_param(params, "color", 0xFFFFFF)
        return frame
