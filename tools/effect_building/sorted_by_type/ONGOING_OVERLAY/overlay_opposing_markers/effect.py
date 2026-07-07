from __future__ import annotations

import hashlib
import math
from typing import Any

from src.core.color_math import blend, scale_color
from src.core.effect_schema import (
    BaseEffect,
    EffectCapabilities,
    EffectDefinition,
    EffectParamDefinition,
    LayerId,
    LayerRule,
    PlaybackMode,
    QueueMode,
    RenderContext,
)

from .common import _merge_params, _param_value, _parse_color, _parse_float, _parse_int, _persistent_state_rules


_PATTERN_ENUM = ("single", "double", "triple", "continuous")
_DECAY_ENUM = ("linear", "quadratic", "exponential")


def _state_rules() -> dict[LayerId, LayerRule]:
    return _persistent_state_rules()


def _overlay_rules() -> dict[LayerId, LayerRule]:
    return {
        LayerId.TEMP_OVERLAY_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
            requires_finite_duration=True,
            allows_transparency=True,
        ),
        LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            requires_indefinite_duration=True,
            allows_transparency=True,
        ),
        LayerId.MAIN_LAYER: LayerRule(
            allowed=True,
            allowed_playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            allows_transparency=True,
        ),
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


def _parse_color_list(value: Any, default: list[int]) -> list[int]:
    if value is None:
        return list(default)
    if isinstance(value, str):
        raw_values = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, (list, tuple)):
        raw_values = list(value)
    else:
        return list(default)

    colors: list[int] = []
    for item in raw_values:
        try:
            colors.append(_parse_color(item, 0))
        except (TypeError, ValueError):
            continue
    return colors or list(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _speed(params: dict[str, Any], default: float) -> float:
    return max(0.0, _parse_float(params.get("speed"), default))


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


def _cycle_phase(now: float, speed: float) -> float:
    if speed <= 0.0:
        return 0.0
    return (now * speed) % 1.0


def _moving_head(now: float, speed: float, led_count: int, *, step_sign: int = 1, offset: int = 0) -> int:
    if led_count <= 0:
        return 0
    return _wrap_index(offset + int(math.floor(now * speed * step_sign)), led_count)


def _palette_sample(colors: list[int], factor: float) -> int:
    if not colors:
        return 0
    if len(colors) == 1:
        return colors[0]
    position = _clamp01(factor) * (len(colors) - 1)
    left = int(math.floor(position))
    right = min(len(colors) - 1, left + 1)
    mix = position - left
    return blend(colors[left], colors[right], mix)


def _decay_factor(index: int, length: int, curve: str) -> float:
    if length <= 1:
        return 1.0
    normalized = 1.0 - (index / float(length - 1))
    if curve == "quadratic":
        return normalized * normalized
    if curve == "exponential":
        return normalized**3
    return normalized


def _event_duration_ms(ctx: RenderContext, params: dict[str, Any], default_ms: int) -> int:
    requested = ctx.invocation.requested_duration_ms
    if requested is None:
        requested = _parse_int(params.get("duration_ms"), default_ms)
    return max(1, int(requested))


def _elapsed_fraction(ctx: RenderContext, params: dict[str, Any], default_ms: int) -> float:
    duration_ms = _event_duration_ms(ctx, params, default_ms)
    elapsed_ms = max(0.0, (ctx.now - ctx.invocation.created_at) * 1000.0)
    return _clamp01(elapsed_ms / float(duration_ms))


def _remaining_ratio_from_timer(ctx: RenderContext, params: dict[str, Any], default_total_ms: int) -> float:
    total_ms = max(1, _parse_int(params.get("total_ms"), default_total_ms))
    if "remaining_ms" in params:
        remaining_ms = max(0, _parse_int(params.get("remaining_ms"), total_ms))
        return _clamp01(remaining_ms / float(total_ms))
    deadline_ts = params.get("deadline_ts")
    if deadline_ts is not None:
        remaining_ms = max(0.0, (float(deadline_ts) - ctx.now) * 1000.0)
        return _clamp01(remaining_ms / float(total_ms))
    elapsed_ms = max(0.0, (ctx.now - ctx.invocation.created_at) * 1000.0)
    remaining_ms = max(0.0, total_ms - elapsed_ms)
    return _clamp01(remaining_ms / float(total_ms))


def _normalized_level(value: Any, default: float) -> float:
    numeric = _parse_float(value, default)
    if numeric > 1.0:
        numeric /= 100.0
    return _clamp01(numeric)


def _resolve_target_led(params: dict[str, Any], led_count: int) -> int:
    if "target_led" in params:
        return _wrap_index(_parse_int(params.get("target_led"), 0), led_count)
    direction = _parse_float(_param_value(params, "direction", "direction_deg"), 0.0) % 360.0
    return _wrap_index(int(round((direction / 360.0) * led_count)), led_count)


def _centered_indices(center: int, size: int, led_count: int) -> list[int]:
    safe_size = max(1, min(size, led_count))
    start = center - ((safe_size - 1) // 2)
    return _segment_indices(start, safe_size, led_count)


def _pattern_centers(pattern: str) -> list[float]:
    if pattern == "double":
        return [0.18, 0.52]
    if pattern == "triple":
        return [0.12, 0.38, 0.64]
    if pattern == "continuous":
        return []
    return [0.2]


def _pattern_intensity(phase: float, pattern: str, *, soft: bool) -> float:
    normalized = _clamp01(phase)
    if pattern == "continuous":
        return 0.5 - 0.5 * math.cos(2.0 * math.pi * normalized) if soft else (1.0 if normalized < 0.5 else 0.0)

    width = {"single": 0.22, "double": 0.16, "triple": 0.12}.get(pattern, 0.22)
    best = 0.0
    for center in _pattern_centers(pattern):
        distance = abs(normalized - center)
        if distance > width:
            continue
        local = 1.0 - (distance / width)
        if soft:
            local = 0.5 - 0.5 * math.cos(math.pi * local)
        else:
            local = 1.0
        best = max(best, local)
    return best


def _flash_window_active(fraction: float, count: int) -> bool:
    if count <= 0:
        return False
    slot = 1.0 / float(max(1, count * 2))
    for index in range(count):
        start = index * slot * 2.0
        end = start + slot
        if start <= fraction <= end:
            return True
    return False


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


def _sparkle_indices(invocation_id: str, bucket: int, led_count: int, count: int) -> list[int]:
    scored: list[tuple[str, int]] = []
    for led_index in range(led_count):
        digest = hashlib.sha1(f"{invocation_id}:{bucket}:{led_index}".encode("utf-8")).hexdigest()
        scored.append((digest, led_index))
    scored.sort()
    return [led_index for _, led_index in scored[: max(0, min(count, led_count))]]


class RotatingSegmentEffect(BaseEffect):
    definition = EffectDefinition(
        id="rotating_segment",
        title="Rotating Segment",
        description="Rotierendes Segment mit Farbe, Hintergrundfarbe und konfigurierbarer Segmentlaenge.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=4.0, minimum=0.0),
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "reverse": _reverse_param(),
            "segment_length": EffectParamDefinition(name="segment_length", type="int", default=3, minimum=1),
        },
        defaults={
            "speed": 4.0,
            "color": "#33AAFF",
            "background_color": "#000000",
            "brightness": 1.0,
            "reverse": False,
            "segment_length": 3,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        tags=("builtin", "state", "animated", "segment"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame = [_background_color(params)] * ctx.led_count
        step_sign = _step_sign(params)
        head = _moving_head(ctx.now, _speed(params, 4.0), ctx.led_count, step_sign=step_sign)
        _paint_segment(
            frame,
            head,
            _parse_int(params.get("segment_length"), 3),
            _color_param(params, "color", 0x33AAFF),
            step_sign=step_sign,
        )
        return frame


class FadingRotatingSegmentEffect(BaseEffect):
    definition = EffectDefinition(
        id="fading_rotating_segment",
        title="Fading Rotating Segment",
        description="Rotierendes Segment mit Helligkeitsabnahme ueber die Segmentlaenge.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=4.0, minimum=0.0),
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "segment_length": EffectParamDefinition(name="segment_length", type="int", default=4, minimum=1),
            "decay_curve": EffectParamDefinition(name="decay_curve", type="enum", default="linear", enum_values=_DECAY_ENUM),
            "reverse": _reverse_param(),
        },
        defaults={
            "speed": 4.0,
            "color": "#33AAFF",
            "background_color": "#000000",
            "brightness": 1.0,
            "segment_length": 4,
            "decay_curve": "linear",
            "reverse": False,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        tags=("builtin", "state", "animated", "segment"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        color = _color_param(params, "color", 0x33AAFF)
        background = _background_color(params)
        length = max(1, _parse_int(params.get("segment_length"), 4))
        curve = str(params.get("decay_curve", "linear")).strip().lower()
        colors = [
            blend(background, color, _decay_factor(index, length, curve))
            for index in range(max(1, min(length, ctx.led_count)))
        ]
        frame = [background] * ctx.led_count
        step_sign = _step_sign(params)
        head = _moving_head(ctx.now, _speed(params, 4.0), ctx.led_count, step_sign=step_sign)
        _paint_segment(frame, head, length, colors, step_sign=step_sign)
        return frame


class RotatingGradientEffect(BaseEffect):
    definition = EffectDefinition(
        id="rotating_gradient",
        title="Rotating Gradient",
        description="Rotierender Farbverlauf ueber den gesamten Ring.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=1.0, minimum=0.0),
            "gradient_colors": EffectParamDefinition(name="gradient_colors", type="color_list", default=("#33AAFF", "#FFAA33")),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "reverse": _reverse_param(),
        },
        defaults={
            "speed": 1.0,
            "gradient_colors": ("#33AAFF", "#FFAA33"),
            "background_color": "#000000",
            "brightness": 1.0,
            "reverse": False,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        tags=("builtin", "state", "animated", "gradient"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        palette = _parse_color_list(params.get("gradient_colors"), [0x33AAFF, 0xFFAA33])
        if not palette:
            return [_background_color(params)] * ctx.led_count
        brightness = _brightness(params, 1.0)
        if brightness < 1.0:
            palette = [scale_color(color, brightness) for color in palette]
        step_sign = _step_sign(params)
        shift = ctx.now * _speed(params, 1.0) * step_sign
        frame: list[int | None] = []
        denominator = max(1, ctx.led_count - 1)
        for led_index in range(ctx.led_count):
            sample = (led_index - shift) % ctx.led_count
            frame.append(_palette_sample(palette, sample / float(denominator)))
        return frame


class ChaseDotEffect(BaseEffect):
    definition = EffectDefinition(
        id="chase_dot",
        title="Chase Dot",
        description="Ein einzelner Laufpunkt mit konfigurierbarer Richtung und Geschwindigkeit.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=6.0, minimum=0.0),
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


class SoftPulsingRingEffect(BaseEffect):
    definition = EffectDefinition(
        id="soft_pulsing_ring",
        title="Soft Pulsing Ring",
        description="Weich pulsierender Ring zwischen minimaler und maximaler Helligkeit.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=0.7, minimum=0.0),
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "min_brightness": EffectParamDefinition(name="min_brightness", type="float", default=0.05, minimum=0.0, maximum=1.0),
            "brightness": _brightness_param(),
        },
        defaults={
            "speed": 0.7,
            "color": "#33AAFF",
            "background_color": "#000000",
            "min_brightness": 0.05,
            "brightness": 1.0,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        tags=("builtin", "state", "animated", "pulse"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        phase = _cycle_phase(ctx.now, _speed(params, 0.7))
        mix = 0.5 - 0.5 * math.cos(2.0 * math.pi * phase)
        min_brightness = _clamp01(_parse_float(params.get("min_brightness"), 0.05))
        brightness = max(min_brightness, _brightness(params, 1.0))
        intensity = min_brightness + ((brightness - min_brightness) * mix)
        color = _raw_color_param(params, "color", 0x33AAFF)
        background = _background_color(params)
        return [blend(background, color, intensity)] * ctx.led_count


class PulsePatternEffect(BaseEffect):
    definition = EffectDefinition(
        id="pulse_pattern",
        title="Pulse Pattern",
        description="Einfacher, doppelter, dreifacher oder dauerhafter Puls auf dem gesamten Ring.",
        parameter_schema={
            "pattern": EffectParamDefinition(name="pattern", type="enum", default="single", enum_values=_PATTERN_ENUM),
            "speed": EffectParamDefinition(name="speed", type="float", default=1.2, minimum=0.0),
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
        },
        defaults={
            "pattern": "single",
            "speed": 1.2,
            "color": "#33AAFF",
            "background_color": "#000000",
            "brightness": 1.0,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        tags=("builtin", "state", "animated", "pulse"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        pattern = str(params.get("pattern", "single")).strip().lower()
        intensity = _pattern_intensity(_cycle_phase(ctx.now, _speed(params, 1.2)), pattern, soft=True)
        intensity *= _brightness(params, 1.0)
        background = _background_color(params)
        color = _raw_color_param(params, "color", 0x33AAFF)
        return [blend(background, color, intensity)] * ctx.led_count


class BlinkPatternEffect(BaseEffect):
    definition = EffectDefinition(
        id="blink_pattern",
        title="Blink Pattern",
        description="Einfaches, doppeltes, dreifaches oder dauerhaftes Blinken.",
        parameter_schema={
            "pattern": EffectParamDefinition(name="pattern", type="enum", default="single", enum_values=_PATTERN_ENUM),
            "speed": EffectParamDefinition(name="speed", type="float", default=1.0, minimum=0.0),
            "color": EffectParamDefinition(name="color", type="color", default="#FFAA33"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
        },
        defaults={"pattern": "single", "speed": 1.0, "color": "#FFAA33", "background_color": "#000000", "brightness": 1.0},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        tags=("builtin", "state", "animated", "blink"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        intensity = _pattern_intensity(
            _cycle_phase(ctx.now, _speed(params, 1.0)),
            str(params.get("pattern", "single")).strip().lower(),
            soft=False,
        )
        return [(_color_param(params, "color", 0xFFAA33) if intensity > 0.0 else _background_color(params))] * ctx.led_count


class RotatingGapEffect(BaseEffect):
    definition = EffectDefinition(
        id="rotating_gap",
        title="Rotating Gap",
        description="Leerlaufender Ring mit rotierender Luecke in einer Vollflaechenfarbe.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=3.0, minimum=0.0),
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "reverse": _reverse_param(),
            "segment_length": EffectParamDefinition(name="segment_length", type="int", default=3, minimum=1),
        },
        defaults={
            "speed": 3.0,
            "color": "#33AAFF",
            "background_color": "#000000",
            "brightness": 1.0,
            "reverse": False,
            "segment_length": 3,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        tags=("builtin", "state", "animated", "segment"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame = [_color_param(params, "color", 0x33AAFF)] * ctx.led_count
        head = _moving_head(
            ctx.now,
            _speed(params, 3.0),
            ctx.led_count,
            step_sign=_step_sign(params),
        )
        _paint_segment(frame, head, _parse_int(params.get("segment_length"), 3), _background_color(params))
        return frame


class RadarSweepEffect(BaseEffect):
    definition = EffectDefinition(
        id="radar_sweep",
        title="Radar Sweep",
        description="Radar-Sweep mit heller Spitze und auslaufendem Schweif.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=5.0, minimum=0.0),
            "color": EffectParamDefinition(name="color", type="color", default="#33FFAA"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "trail_length": EffectParamDefinition(name="trail_length", type="int", default=5, minimum=1),
            "reverse": _reverse_param(),
        },
        defaults={
            "speed": 5.0,
            "color": "#33FFAA",
            "background_color": "#000000",
            "brightness": 1.0,
            "trail_length": 5,
            "reverse": False,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        tags=("builtin", "state", "animated", "sweep"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        background = _background_color(params)
        color = _color_param(params, "color", 0x33FFAA)
        step_sign = _step_sign(params)
        trail_length = max(1, _parse_int(params.get("trail_length"), 5))
        head = _moving_head(ctx.now, _speed(params, 5.0), ctx.led_count, step_sign=step_sign)
        frame = [background] * ctx.led_count
        for step in range(trail_length):
            index = _wrap_index(head - (step * step_sign), ctx.led_count)
            frame[index] = blend(background, color, _decay_factor(step, trail_length, "exponential"))
        return frame


class ScannerEffect(BaseEffect):
    definition = EffectDefinition(
        id="scanner",
        title="Scanner",
        description="Hin- und herlaufendes Segment mit fester Segmentlaenge.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=6.0, minimum=0.0),
            "color": EffectParamDefinition(name="color", type="color", default="#FF3344"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "segment_length": EffectParamDefinition(name="segment_length", type="int", default=3, minimum=1),
        },
        defaults={"speed": 6.0, "color": "#FF3344", "background_color": "#000000", "brightness": 1.0, "segment_length": 3},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        tags=("builtin", "state", "animated", "scanner"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame = [_background_color(params)] * ctx.led_count
        segment_length = max(1, min(ctx.led_count, _parse_int(params.get("segment_length"), 3)))
        travel = max(0, ctx.led_count - segment_length)
        if travel == 0:
            _paint_segment(frame, 0, segment_length, _color_param(params, "color", 0xFF3344))
            return frame
        position = (ctx.now * _speed(params, 6.0)) % (travel * 2)
        start = int(math.floor(position)) if position <= travel else int(math.floor((travel * 2) - position))
        _paint_segment(frame, start, segment_length, _color_param(params, "color", 0xFF3344))
        return frame


class YinYangSpinEffect(BaseEffect):
    definition = EffectDefinition(
        id="yin_yang_spin",
        title="Yin Yang Spin",
        description="Rotierender Yin-Yang-Effekt mit zwei Farben, Richtung und Trennschaerfe.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=1.5, minimum=0.0),
            "color_a": EffectParamDefinition(name="color_a", type="color", default="#FFFFFF"),
            "color_b": EffectParamDefinition(name="color_b", type="color", default="#111111"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "sharpness": EffectParamDefinition(name="sharpness", type="float", default=0.9, minimum=0.0, maximum=1.0),
            "reverse": _reverse_param(),
        },
        defaults={
            "speed": 1.5,
            "color_a": "#FFFFFF",
            "color_b": "#111111",
            "background_color": "#000000",
            "brightness": 1.0,
            "sharpness": 0.9,
            "reverse": False,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules=_state_rules(),
        tags=("builtin", "state", "animated", "duotone"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        color_a = _color_param(params, "color_a", 0xFFFFFF, "color_1")
        color_b = _color_param(params, "color_b", 0x111111, "color_2")
        background = _background_color(params)
        sharpness = _clamp01(_parse_float(params.get("sharpness", params.get("trennschaerfe")), 0.9))
        soft_zone = max(0.01, (1.0 - sharpness) * 0.5)
        step_sign = _step_sign(params)
        shift = ctx.now * _speed(params, 1.5) * step_sign
        frame: list[int | None] = []
        for led_index in range(ctx.led_count):
            position = ((led_index - shift) % ctx.led_count) / float(max(1, ctx.led_count))
            distance = abs(position - 0.5)
            if distance > soft_zone:
                base = color_a if position < 0.5 else color_b
            else:
                mix = (position - (0.5 - soft_zone)) / float(max(soft_zone * 2.0, 0.0001))
                base = blend(color_a, color_b, _clamp01(mix))
            frame.append(blend(background, base, 1.0))
        return frame


class FillRingEffect(BaseEffect):
    definition = EffectDefinition(
        id="fill_ring",
        title="Fill Ring",
        description="Ringfoermiger Fuellstand mit Richtung und Start-LED.",
        parameter_schema={
            "fill_level": EffectParamDefinition(name="fill_level", type="float", default=0.0, minimum=0.0, maximum=100.0),
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "reverse": _reverse_param(),
            "start_led": EffectParamDefinition(name="start_led", type="int", default=0, minimum=0),
        },
        defaults={
            "fill_level": 0.0,
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
        tags=("builtin", "overlay", "progress"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        ratio = _normalized_level(params.get("fill_level"), 0.0)
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


class ProgressRingEffect(BaseEffect):
    definition = EffectDefinition(
        id="progress_ring",
        title="Progress Ring",
        description="Ringfoermiger Fortschritt mit Richtung und Start-LED.",
        parameter_schema={
            "progress_value": EffectParamDefinition(name="progress_value", type="float", default=0.0, minimum=0.0, maximum=100.0),
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "reverse": _reverse_param(),
            "start_led": EffectParamDefinition(name="start_led", type="int", default=0, minimum=0),
        },
        defaults={
            "progress_value": 0.0,
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
        tags=("builtin", "overlay", "progress"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        params["fill_level"] = params.get("progress_value", 0.0)
        return FillRingEffect().render(
            RenderContext(
                now=ctx.now,
                led_count=ctx.led_count,
                layer_id=ctx.layer_id,
                definition=self.definition,
                invocation=ctx.invocation,
                params=params,
            )
        )


class TimerRingEffect(BaseEffect):
    definition = EffectDefinition(
        id="timer_ring",
        title="Timer Ring",
        description="Zeigt die verbleibende Zeit relativ zur Gesamtzeit auf dem Ring an.",
        parameter_schema={
            "remaining_ms": EffectParamDefinition(name="remaining_ms", type="duration_ms", required=False),
            "total_ms": EffectParamDefinition(name="total_ms", type="duration_ms", default=1000, minimum=1, unit="ms"),
            "deadline_ts": EffectParamDefinition(name="deadline_ts", type="float", required=False),
            "color": EffectParamDefinition(name="color", type="color", default="#FF9F1A"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "reverse": _reverse_param(),
        },
        defaults={
            "total_ms": 1000,
            "color": "#FF9F1A",
            "background_color": "#000000",
            "brightness": 1.0,
            "reverse": False,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_transparency=True,
            supports_duration_override=True,
            restorable=True,
        ),
        layer_rules=_overlay_rules(),
        tags=("builtin", "overlay", "timer"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        ratio = _remaining_ratio_from_timer(ctx, params, 1000)
        count = int(round(ratio * ctx.led_count))
        frame = [_background_color(params)] * ctx.led_count
        start = 0 if _step_sign(params) >= 0 else ctx.led_count - 1
        _paint_segment(
            frame,
            start,
            count,
            _color_param(params, "color", 0xFF9F1A),
            step_sign=_step_sign(params),
        )
        return frame


class CountdownSegmentEffect(BaseEffect):
    definition = EffectDefinition(
        id="countdown_segment",
        title="Countdown Segment",
        description="Countdown als schrumpfendes Segment mit Richtung und Gesamtzeit.",
        parameter_schema={
            "remaining_ms": EffectParamDefinition(name="remaining_ms", type="duration_ms", required=False),
            "total_ms": EffectParamDefinition(name="total_ms", type="duration_ms", default=1000, minimum=1, unit="ms"),
            "deadline_ts": EffectParamDefinition(name="deadline_ts", type="float", required=False),
            "color": EffectParamDefinition(name="color", type="color", default="#FF9F1A"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "segment_length": EffectParamDefinition(name="segment_length", type="int", default=6, minimum=1),
            "reverse": _reverse_param(),
        },
        defaults={
            "total_ms": 1000,
            "color": "#FF9F1A",
            "background_color": "#000000",
            "brightness": 1.0,
            "segment_length": 6,
            "reverse": False,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_transparency=True,
            supports_duration_override=True,
            restorable=True,
        ),
        layer_rules=_overlay_rules(),
        tags=("builtin", "overlay", "timer", "segment"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        ratio = _remaining_ratio_from_timer(ctx, params, 1000)
        base_length = max(1, _parse_int(params.get("segment_length"), 6))
        active_length = int(round(base_length * ratio))
        frame = [_background_color(params)] * ctx.led_count
        start = 0 if _step_sign(params) >= 0 else ctx.led_count - 1
        _paint_segment(
            frame,
            start,
            active_length,
            _color_param(params, "color", 0xFF9F1A),
            step_sign=_step_sign(params),
        )
        return frame


class DoaDirectionDotEffect(BaseEffect):
    definition = EffectDefinition(
        id="doa_direction_dot",
        title="DoA Direction Dot",
        description="Richtungspunkt fuer DoA mit Ziel-LED oder Winkel und konfigurierbarer Punktgroesse.",
        parameter_schema={
            "direction": EffectParamDefinition(name="direction", type="float", default=0.0),
            "target_led": EffectParamDefinition(name="target_led", type="int", required=False),
            "color": EffectParamDefinition(name="color", type="color", default="#EAF8FF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "point_size": EffectParamDefinition(name="point_size", type="int", default=1, minimum=1),
        },
        defaults={
            "direction": 0.0,
            "color": "#EAF8FF",
            "background_color": "#000000",
            "brightness": 1.0,
            "point_size": 1,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_transparency=True,
            restorable=True,
        ),
        layer_rules=_overlay_rules(),
        tags=("builtin", "overlay", "direction"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        center = _resolve_target_led(params, ctx.led_count)
        frame = [_background_color(params)] * ctx.led_count
        for led_index in _centered_indices(center, max(1, _parse_int(params.get("point_size"), 1)), ctx.led_count):
            frame[led_index] = _color_param(params, "color", 0xEAF8FF)
        return frame


class DoaDirectionSegmentEffect(BaseEffect):
    definition = EffectDefinition(
        id="doa_direction_segment",
        title="DoA Direction Segment",
        description="Richtungssegment fuer DoA mit Ziel-LED oder Winkel.",
        parameter_schema={
            "direction": EffectParamDefinition(name="direction", type="float", default=0.0),
            "target_led": EffectParamDefinition(name="target_led", type="int", required=False),
            "color": EffectParamDefinition(name="color", type="color", default="#7FC9FF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "segment_length": EffectParamDefinition(name="segment_length", type="int", default=3, minimum=1),
        },
        defaults={
            "direction": 0.0,
            "color": "#7FC9FF",
            "background_color": "#000000",
            "brightness": 1.0,
            "segment_length": 3,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_transparency=True,
            restorable=True,
        ),
        layer_rules=_overlay_rules(),
        tags=("builtin", "overlay", "direction"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        center = _resolve_target_led(params, ctx.led_count)
        size = max(1, _parse_int(params.get("segment_length"), 3))
        frame = [_background_color(params)] * ctx.led_count
        for led_index in _centered_indices(center, size, ctx.led_count):
            frame[led_index] = _color_param(params, "color", 0x7FC9FF)
        return frame


class HighlightedSegmentEffect(BaseEffect):
    definition = EffectDefinition(
        id="highlighted_segment",
        title="Highlighted Segment",
        description="Hebt ein Segment an einer Position mit eigener Helligkeit hervor.",
        parameter_schema={
            "position": EffectParamDefinition(name="position", type="int", default=0, minimum=0),
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "segment_length": EffectParamDefinition(name="segment_length", type="int", default=3, minimum=1),
            "brightness": EffectParamDefinition(name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0),
        },
        defaults={
            "position": 0,
            "color": "#33AAFF",
            "background_color": "#000000",
            "segment_length": 3,
            "brightness": 1.0,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_transparency=True,
            restorable=True,
        ),
        layer_rules=_overlay_rules(),
        tags=("builtin", "overlay", "segment"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame = [_background_color(params)] * ctx.led_count
        color = _color_param(params, "color", 0x33AAFF)
        _paint_segment(frame, _parse_int(params.get("position"), 0), _parse_int(params.get("segment_length"), 3), color)
        return frame


class OpposingMarkersEffect(BaseEffect):
    definition = EffectDefinition(
        id="opposing_markers",
        title="Opposing Markers",
        description="Zwei gegensaetzliche Marker mit eigener Position und Farbe.",
        parameter_schema={
            "position_a": EffectParamDefinition(name="position_a", type="int", default=0, minimum=0),
            "position_b": EffectParamDefinition(name="position_b", type="int", required=False),
            "color_a": EffectParamDefinition(name="color_a", type="color", default="#33AAFF"),
            "color_b": EffectParamDefinition(name="color_b", type="color", default="#FFAA33"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
        },
        defaults={
            "position_a": 0,
            "color_a": "#33AAFF",
            "color_b": "#FFAA33",
            "background_color": "#000000",
            "brightness": 1.0,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_transparency=True,
            restorable=True,
        ),
        layer_rules=_overlay_rules(),
        tags=("builtin", "overlay", "markers"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame = [_background_color(params)] * ctx.led_count
        position_a = _wrap_index(_parse_int(params.get("position_a"), 0), ctx.led_count)
        default_b = position_a + (ctx.led_count // 2)
        position_b = _wrap_index(_parse_int(params.get("position_b"), default_b), ctx.led_count)
        frame[position_a] = _color_param(params, "color_a", 0x33AAFF)
        frame[position_b] = _color_param(params, "color_b", 0xFFAA33)
        return frame


class ShortFlashEffect(BaseEffect):
    definition = EffectDefinition(
        id="short_flash",
        title="Short Flash",
        description="Kurzes Aufblitzen mit Farbe, Hintergrund und Dauer.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#FFFFFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=250, minimum=1, unit="ms"),
        },
        defaults={"color": "#FFFFFF", "background_color": "#000000", "brightness": 1.0, "duration_ms": 250},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
        ),
        layer_rules=_event_rules(),
        tags=("builtin", "event", "flash"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame_color = _color_param(params, "color", 0xFFFFFF) if _flash_active_at_elapsed(ctx, params, 1, 250) else _background_color(params)
        return [frame_color] * ctx.led_count


class DoubleFlashEffect(BaseEffect):
    definition = EffectDefinition(
        id="double_flash",
        title="Double Flash",
        description="Doppeltes Aufblitzen mit Dauer und Pause.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#FFFFFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=500, minimum=1, unit="ms"),
            "pause_ms": EffectParamDefinition(name="pause_ms", type="duration_ms", default=120, minimum=0, unit="ms"),
        },
        defaults={"color": "#FFFFFF", "background_color": "#000000", "brightness": 1.0, "duration_ms": 500, "pause_ms": 120},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
        ),
        layer_rules=_event_rules(),
        tags=("builtin", "event", "flash"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame_color = _color_param(params, "color", 0xFFFFFF) if _flash_active_at_elapsed(ctx, params, 2, 500) else _background_color(params)
        return [frame_color] * ctx.led_count


class TripleFlashEffect(BaseEffect):
    definition = EffectDefinition(
        id="triple_flash",
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
        tags=("builtin", "event", "flash"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame_color = _color_param(params, "color", 0xFFFFFF) if _flash_active_at_elapsed(ctx, params, 3, 700) else _background_color(params)
        return [frame_color] * ctx.led_count


class ShortPulseEffect(BaseEffect):
    definition = EffectDefinition(
        id="short_pulse",
        title="Short Pulse",
        description="Kurzer Puls mit konfigurierbarer Maximalhelligkeit.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "speed": EffectParamDefinition(name="speed", type="float", default=1.0, minimum=0.0),
            "brightness": _brightness_param(),
            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=500, minimum=1, unit="ms"),
        },
        defaults={
            "color": "#33AAFF",
            "background_color": "#000000",
            "speed": 1.0,
            "brightness": 1.0,
            "duration_ms": 500,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
        ),
        layer_rules=_event_rules(),
        tags=("builtin", "event", "pulse"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        phase = _elapsed_fraction(ctx, params, 500)
        wave = max(0.0, math.sin(math.pi * _speed(params, 1.0) * phase))
        intensity = wave * _brightness(params, 1.0)
        return [blend(_background_color(params), _raw_color_param(params, "color", 0x33AAFF), intensity)] * ctx.led_count


class ShortSoftPulseEffect(BaseEffect):
    definition = EffectDefinition(
        id="short_soft_pulse",
        title="Short Soft Pulse",
        description="Kurzer weicher Puls zwischen minimaler und maximaler Helligkeit.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "speed": EffectParamDefinition(name="speed", type="float", default=1.0, minimum=0.0),
            "min_brightness": EffectParamDefinition(name="min_brightness", type="float", default=0.1, minimum=0.0, maximum=1.0),
            "brightness": _brightness_param(),
            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=650, minimum=1, unit="ms"),
        },
        defaults={
            "color": "#33AAFF",
            "background_color": "#000000",
            "speed": 1.0,
            "min_brightness": 0.1,
            "brightness": 1.0,
            "duration_ms": 650,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
        ),
        layer_rules=_event_rules(),
        tags=("builtin", "event", "pulse"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        phase = _elapsed_fraction(ctx, params, 650)
        mix = 0.5 - 0.5 * math.cos(2.0 * math.pi * _speed(params, 1.0) * phase)
        min_brightness = _clamp01(_parse_float(params.get("min_brightness"), 0.1))
        brightness = max(min_brightness, _brightness(params, 1.0))
        intensity = min_brightness + ((brightness - min_brightness) * mix)
        return [blend(_background_color(params), _raw_color_param(params, "color", 0x33AAFF), intensity)] * ctx.led_count


class BlinkImpulseEffect(BaseEffect):
    definition = EffectDefinition(
        id="blink_impulse",
        title="Blink Impulse",
        description="Kurzer Blink-Impuls mit harter Umschaltung.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#FFFFFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=220, minimum=1, unit="ms"),
        },
        defaults={"color": "#FFFFFF", "background_color": "#000000", "brightness": 1.0, "duration_ms": 220},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
        ),
        layer_rules=_event_rules(),
        tags=("builtin", "event", "blink"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        phase = _elapsed_fraction(ctx, params, 220)
        frame_color = _color_param(params, "color", 0xFFFFFF) if phase <= 0.35 else _background_color(params)
        return [frame_color] * ctx.led_count


class ShortRunningDotEffect(BaseEffect):
    definition = EffectDefinition(
        id="short_running_dot",
        title="Short Running Dot",
        description="Kurzer Laufpunkt ueber den Event-Layer.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=1.0, minimum=0.0),
            "color": EffectParamDefinition(name="color", type="color", default="#FFFFFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "reverse": _reverse_param(),
            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=700, minimum=1, unit="ms"),
        },
        defaults={
            "speed": 1.0,
            "color": "#FFFFFF",
            "background_color": "#000000",
            "brightness": 1.0,
            "reverse": False,
            "duration_ms": 700,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
        ),
        layer_rules=_event_rules(),
        tags=("builtin", "event", "dot"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame = [_background_color(params)] * ctx.led_count
        phase = _elapsed_fraction(ctx, params, 700)
        step_sign = _step_sign(params)
        origin = 0 if step_sign >= 0 else ctx.led_count - 1
        distance = phase * max(1, ctx.led_count - 1) * max(1.0, _speed(params, 1.0))
        head = _wrap_index(origin + int(math.floor(distance * step_sign)), ctx.led_count)
        frame[head] = _color_param(params, "color", 0xFFFFFF)
        return frame


class ShortSweepEffect(BaseEffect):
    definition = EffectDefinition(
        id="short_sweep",
        title="Short Sweep",
        description="Kurzer Sweep mit konfigurierbarer Segmentlaenge.",
        parameter_schema={
            "speed": EffectParamDefinition(name="speed", type="float", default=1.0, minimum=0.0),
            "color": EffectParamDefinition(name="color", type="color", default="#33FFAA"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "reverse": _reverse_param(),
            "segment_length": EffectParamDefinition(name="segment_length", type="int", default=4, minimum=1),
            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=700, minimum=1, unit="ms"),
        },
        defaults={
            "speed": 1.0,
            "color": "#33FFAA",
            "background_color": "#000000",
            "brightness": 1.0,
            "reverse": False,
            "segment_length": 4,
            "duration_ms": 700,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
        ),
        layer_rules=_event_rules(),
        tags=("builtin", "event", "sweep"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame = [_background_color(params)] * ctx.led_count
        phase = _elapsed_fraction(ctx, params, 700)
        step_sign = _step_sign(params)
        origin = 0 if step_sign >= 0 else ctx.led_count - 1
        distance = phase * max(1, ctx.led_count - 1) * max(1.0, _speed(params, 1.0))
        head = _wrap_index(origin + int(math.floor(distance * step_sign)), ctx.led_count)
        _paint_segment(
            frame,
            head,
            _parse_int(params.get("segment_length"), 4),
            _color_param(params, "color", 0x33FFAA),
            step_sign=step_sign,
        )
        return frame


class SparkleBurstEffect(BaseEffect):
    definition = EffectDefinition(
        id="sparkle_burst",
        title="Sparkle Burst",
        description="Kurzer Sparkle-Effekt mit zufaelligen LEDs ueber den Event-Layer.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#FFFFFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "sparkle_count": EffectParamDefinition(name="sparkle_count", type="int", default=3, minimum=1),
            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=650, minimum=1, unit="ms"),
        },
        defaults={"color": "#FFFFFF", "background_color": "#000000", "brightness": 1.0, "sparkle_count": 3, "duration_ms": 650},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
        ),
        layer_rules=_event_rules(),
        tags=("builtin", "event", "sparkle"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame = [_background_color(params)] * ctx.led_count
        bucket = int(math.floor(_elapsed_fraction(ctx, params, 650) * 8.0))
        for led_index in _sparkle_indices(
            ctx.invocation.invocation_id,
            bucket,
            ctx.led_count,
            _parse_int(params.get("sparkle_count", params.get("random_led_count")), 3),
        ):
            frame[led_index] = _color_param(params, "color", 0xFFFFFF)
        return frame


class ShortPingEffect(BaseEffect):
    definition = EffectDefinition(
        id="short_ping",
        title="Short Ping",
        description="Kurzer Ping mit Start-LED, Richtung und auslaufendem Schweif.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "background_color": EffectParamDefinition(name="background_color", type="color", default="#000000"),
            "brightness": _brightness_param(),
            "start_led": EffectParamDefinition(name="start_led", type="int", default=0, minimum=0),
            "reverse": _reverse_param(),
            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=700, minimum=1, unit="ms"),
        },
        defaults={
            "color": "#33AAFF",
            "background_color": "#000000",
            "brightness": 1.0,
            "start_led": 0,
            "reverse": False,
            "duration_ms": 700,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
        ),
        layer_rules=_event_rules(),
        tags=("builtin", "event", "ping"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        frame = [_background_color(params)] * ctx.led_count
        phase = _elapsed_fraction(ctx, params, 700)
        step_sign = _step_sign(params)
        start_led = _wrap_index(_parse_int(params.get("start_led"), 0), ctx.led_count)
        head = _wrap_index(start_led + int(math.floor(phase * max(1, ctx.led_count - 1) * step_sign)), ctx.led_count)
        trail_length = min(4, ctx.led_count)
        for step in range(trail_length):
            index = _wrap_index(head - (step * step_sign), ctx.led_count)
            frame[index] = blend(_background_color(params), _raw_color_param(params, "color", 0x33AAFF), _decay_factor(step, trail_length, "quadratic"))
        return frame
