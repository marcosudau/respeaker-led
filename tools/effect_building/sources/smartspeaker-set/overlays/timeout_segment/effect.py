from __future__ import annotations

import math
from typing import Any

from respeaker_led.core.color_math import blend, scale_color
from respeaker_led.core.effect_schema import (
    BaseEffect,
    ColorModel,
    CompositionMode,
    DefinitionType,
    EffectCapabilities,
    EffectDefinition,
    EffectParamDefinition,
    InputSamplingPolicy,
    LayerId,
    LayerRule,
    OverlayMode,
    PlaybackMode,
    QueueMode,
    RenderContext,
)


def _params(ctx: RenderContext) -> dict[str, Any]:
    values = dict(ctx.definition.defaults)
    values.update(ctx.params)
    values.update(ctx.inputs)
    return values


def _color(value: Any, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value & 0xFFFFFF
    text = str(value).strip()
    if text.startswith('#'):
        text = text[1:]
    elif text.lower().startswith('0x'):
        text = text[2:]
    try:
        return int(text, 16) & 0xFFFFFF
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'1', 'true', 'yes', 'on'}:
            return True
        if normalized in {'0', 'false', 'no', 'off'}:
            return False
    return default


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _brightness(params: dict[str, Any]) -> float:
    return _clamp01(_float(params.get('brightness'), 1.0))


def _scaled(params: dict[str, Any], key: str, default: int, factor: float = 1.0) -> int:
    return scale_color(_color(params.get(key), default), _clamp01(_brightness(params) * factor))


def _elapsed(ctx: RenderContext) -> float:
    return max(0.0, ctx.now - ctx.invocation.created_at)


def _duration_ms(ctx: RenderContext, params: dict[str, Any], default: int) -> int:
    requested = ctx.invocation.requested_duration_ms
    value = requested if requested is not None else _int(params.get('duration_ms'), default)
    return max(1, int(value))


def _progress(ctx: RenderContext, params: dict[str, Any], default_ms: int) -> float:
    return _clamp01((_elapsed(ctx) * 1000.0) / float(_duration_ms(ctx, params, default_ms)))


def _direction(params: dict[str, Any]) -> int:
    return -1 if _bool(params.get('reverse'), False) else 1


def _state_rules() -> dict[LayerId, LayerRule]:
    return {
        LayerId.STATE_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            requires_indefinite_duration=True,
        )
    }


def _controlled_overlay_rules(*, transparent: bool) -> dict[LayerId, LayerRule]:
    return {
        LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            requires_indefinite_duration=True,
            allows_transparency=transparent,
        )
    }


def _timed_overlay_rules(*, transparent: bool) -> dict[LayerId, LayerRule]:
    return {
        LayerId.TEMP_OVERLAY_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
            requires_finite_duration=True,
            allows_transparency=transparent,
        )
    }


def _event_rules() -> dict[LayerId, LayerRule]:
    return {
        LayerId.EVENT_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
            requires_finite_duration=True,
            queue_mode=QueueMode.PRIORITY_FIFO,
        )
    }


def _paint(frame: list[int | None], start: int, length: int, color: int, step: int = 1) -> None:
    count = len(frame)
    if count <= 0:
        return
    for offset in range(max(0, min(int(length), count))):
        frame[(start + offset * step) % count] = color


def _breath(elapsed: float, speed: float, minimum: float) -> float:
    # speed is a multiplier around a calm 3.5-second base period.
    phase = (elapsed * max(0.05, speed) / 3.5) % 1.0
    wave = 0.5 - 0.5 * math.cos(2.0 * math.pi * phase)
    return _clamp01(minimum + (1.0 - minimum) * wave)


def _palette(value: Any, fallback: tuple[int, ...]) -> list[int]:
    if not isinstance(value, (list, tuple)):
        return list(fallback)
    colors = [_color(item, 0) for item in value]
    return colors or list(fallback)


class TimeoutSegmentOverlay(BaseEffect):
    definition = EffectDefinition(
        id='timeout_segment',
        title='Timeout-Segment',
        description='Ein warmes Segment schmilzt ruhig und gleichmäßig bis auf null ab.',
        definition_type=DefinitionType.OVERLAY,
        overlay_mode=OverlayMode.TIMED,
        parameter_schema={
            'color': EffectParamDefinition(name='color', type='color', default='#FFD166'),
            'brightness': EffectParamDefinition(name='brightness', type='float', default=1.0, minimum=0.0, maximum=1.0, unit='ratio'),
            'duration_ms': EffectParamDefinition(name='duration_ms', type='duration_ms', default=5000, minimum=100, maximum=3600000, unit='ms'),
            'reverse': EffectParamDefinition(name='reverse', type='bool', default=False),
            'segment_length': EffectParamDefinition(name='segment_length', type='int', default=6, minimum=1, maximum=12),
        },
        defaults={
            'color': '#FFD166',
            'brightness': 0.72,
            'duration_ms': 5000,
            'reverse': False,
            'segment_length': 6,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,), supports_transparency=True, supports_duration_override=True
        ),
        layer_rules=_timed_overlay_rules(transparent=True),
        color_model=ColorModel.MONO,
        composition=CompositionMode.TRANSPARENT,
        animated=False,
        directional=True,
        tags=('smartspeaker-set', 'overlay', 'timeout'),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _params(ctx)
        frame: list[int | None] = [None] * ctx.led_count
        if not ctx.led_count:
            return frame
        remaining = 1.0 - _progress(ctx, params, 5000)
        maximum = max(1, min(ctx.led_count, _int(params.get('segment_length'), 6)))
        exact = remaining * maximum
        full = int(math.floor(exact))
        step = _direction(params)
        base = 0 if step > 0 else ctx.led_count - 1
        color = _scaled(params, 'color', 0xFFD166)
        for offset in range(full):
            frame[(base + offset * step) % ctx.led_count] = color
        if full < maximum and exact > full:
            frame[(base + full * step) % ctx.led_count] = _scaled(params, 'color', 0xFFD166, exact - full)
        return frame
