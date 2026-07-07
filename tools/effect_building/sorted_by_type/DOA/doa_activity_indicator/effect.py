from __future__ import annotations

from typing import Any

from src.core.effect_schema import (
    BaseEffect,
    EffectCapabilities,
    EffectDefinition,
    EffectParamDefinition,
    LayerId,
    LayerRule,
    PlaybackMode,
    RenderContext,
)

from .common import _merge_params, _parse_color, _parse_float, _parse_int


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


def _resolve_center_led(direction: float, led_count: int, angle_offset_deg: float, reverse: bool) -> int:
    normalized = (float(direction) + float(angle_offset_deg)) % 360.0
    if reverse:
        normalized = (-normalized) % 360.0
    return int(round((normalized / 360.0) * led_count)) % led_count


class DoaActivityIndicatorEffect(BaseEffect):
    definition = EffectDefinition(
        id="doa_activity_indicator",
        title="DoA Activity Indicator",
        description="Rendert einen DoA-Richtungsindikator mit Wings fuer Sound- oder Speech-Erkennung.",
        parameter_schema={
            "direction": EffectParamDefinition(name="direction", type="float", required=False),
            "detection_state": EffectParamDefinition(
                name="detection_state",
                type="enum",
                default="sound",
                enum_values=("sound", "speech"),
            ),
            "angle_offset_deg": EffectParamDefinition(name="angle_offset_deg", type="float", default=0.0),
            "reverse": EffectParamDefinition(name="reverse", type="bool", default=False),
            "wing_count": EffectParamDefinition(name="wing_count", type="int", default=0, minimum=0),
            "center_color": EffectParamDefinition(name="center_color", type="color", default="#7FC9FF"),
            "side_color": EffectParamDefinition(name="side_color", type="color", default="#B8EBFF"),
            "speech_center_color": EffectParamDefinition(name="speech_center_color", type="color", default="#D8FFF0"),
            "speech_side_color": EffectParamDefinition(name="speech_side_color", type="color", default="#33FFAA"),
        },
        defaults={
            "detection_state": "sound",
            "angle_offset_deg": 0.0,
            "reverse": False,
            "wing_count": 0,
            "center_color": "#7FC9FF",
            "side_color": "#B8EBFF",
            "speech_center_color": "#D8FFF0",
            "speech_side_color": "#33FFAA",
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_transparency=True,
            restorable=True,
        ),
        layer_rules={
            LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                requires_indefinite_duration=True,
                allows_transparency=True,
            ),
        },
        tags=("builtin", "overlay", "direction", "doa"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        direction = params.get("direction")
        if direction is None:
            return [None] * ctx.led_count

        detection_state = str(params.get("detection_state", "sound")).strip().lower()
        if detection_state not in {"sound", "speech"}:
            detection_state = "sound"

        center_led = _resolve_center_led(
            _parse_float(direction, 0.0),
            ctx.led_count,
            _parse_float(params.get("angle_offset_deg"), 0.0),
            _parse_bool(params.get("reverse"), False),
        )
        wing_count = max(0, _parse_int(params.get("wing_count"), 0))

        if detection_state == "speech":
            center_color = _parse_color(params.get("speech_center_color"), 0xD8FFF0)
            side_color = _parse_color(params.get("speech_side_color"), 0x33FFAA)
        else:
            center_color = _parse_color(params.get("center_color"), 0x7FC9FF)
            side_color = _parse_color(params.get("side_color"), 0xB8EBFF)

        frame: list[int | None] = [None] * ctx.led_count
        frame[center_led] = center_color
        for offset in range(1, wing_count + 1):
            frame[(center_led - offset) % ctx.led_count] = side_color
            frame[(center_led + offset) % ctx.led_count] = side_color
        return frame