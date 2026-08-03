from __future__ import annotations

from typing import Any
import math
from src.core.color_math import scale_color
from src.core.effect_schema import (
    BaseEffect,
    ColorModel,
    CompositionMode,
    DefinitionType,
    EffectCapabilities,
    EffectDefinition,
    EffectParamDefinition,
    InputMode,
    InputSamplingPolicy,
    LayerId,
    LayerRule,
    OverlayMode,
    PlaybackMode,
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


class Effect(BaseEffect):
    definition = EffectDefinition(
        id="direction_indicator",
        title="DoA Direction Indicator",
        description=(
            "Zeigt bei aktiver Voice Activity genau eine Richtungs-LED und "
            "laesst den darunterliegenden State unveraendert sichtbar."
        ),
        definition_type=DefinitionType.OVERLAY,
        overlay_mode=OverlayMode.CONTROLLED,
        parameter_schema={
            "color": EffectParamDefinition(
                name="color",
                type="color",
                default="#00C066",
            ),
            "brightness": EffectParamDefinition(
                name="brightness",
                type="float",
                default=1.0,
                minimum=0.0,
                maximum=1.0,
                unit="ratio",
            ),
            "angle_offset_deg": EffectParamDefinition(
                name="angle_offset_deg",
                type="float",
                default=0.0,
                minimum=-180.0,
                maximum=180.0,
                unit="deg",
            ),
            "reverse": EffectParamDefinition(
                name="reverse",
                type="bool",
                default=False,
            ),
        },
        runtime_input_schema={
            "direction_deg": EffectParamDefinition(
                name="direction_deg",
                type="angle_deg",
                required=True,
                nullable=True,
                unit="deg",
                aliases=("direction",),
            ),
            "detection_state": EffectParamDefinition(
                name="detection_state",
                type="enum",
                default="none",
                enum_values=("none", "sound", "speech"),
            ),
        },
        defaults={
            "color": "#00C066",
            "brightness": 1.0,
            "angle_offset_deg": 0.0,
            "reverse": False,
        },
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_transparency=True,
            restorable=True,
            data_driven=True,
        ),
        layer_rules={
            LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                requires_indefinite_duration=True,
                allows_transparency=True,
            ),
        },
        color_model=ColorModel.MONO,
        composition=CompositionMode.TRANSPARENT,
        animated=False,
        directional=True,
        input_sampling=InputSamplingPolicy(
            mode=InputMode.PULL,
            provider_id="respeaker_doa",
            interval_ms=0,
            heartbeat_interval_ms=1000,
            max_missed_heartbeats=3,
        ),
        tags=("builtin", "overlay", "direction", "doa"),
    )

    def render2(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        direction = params.get("direction_deg")
        detection_state = str(params.get("detection_state", "none")).strip().lower()
        if (
            direction is None
            or detection_state not in {"sound", "speech"}
            or ctx.led_count <= 0
        ):
            return [None] * ctx.led_count
        direction_deg = (
            _parse_float(direction, 0.0)
            + _parse_float(params.get("angle_offset_deg"), 0.0)
        ) % 360.0
        if bool(params.get("reverse", False)):
            direction_deg = (-direction_deg) % 360.0
        center = int(round((direction_deg / 360.0) * ctx.led_count)) % ctx.led_count
        color = _parse_color(params.get("color"), 0x00C066)
        brightness = min(1.0, max(0.0, _parse_float(params.get("brightness"), 1.0)))
        if brightness < 1.0:
            color = scale_color(color, brightness)
        colors: list[int | None] = [None] * ctx.led_count
        colors[center] = color
        return colors

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)

        direction = params.get("direction_deg")
        detection_state = str(
            params.get("detection_state", "none")
        ).strip().lower()

        if (
            direction is None
            or detection_state not in {"sound", "speech"}
            or ctx.led_count <= 0
        ):
            return [None] * ctx.led_count

        # Absoluten Messwinkel des ReSpeakers einlesen.
        raw_direction_deg = _parse_float(direction, 0.0) % 360.0

        # Die Messrichtung spiegeln, ohne dabei den festen Offset zu spiegeln.
        if bool(params.get("reverse", False)):
            raw_direction_deg = (-raw_direction_deg) % 360.0

        # Der Offset beschreibt danach ausschließlich die physische Ausrichtung
        # zwischen ReSpeaker-Winkel und LED-Indexierung.
        angle_offset_deg = _parse_float(
            params.get("angle_offset_deg"),
            0.0,
        )

        mapped_direction_deg = (
            raw_direction_deg + angle_offset_deg
        ) % 360.0

        # Eindeutige Rundung auf die nächstgelegene LED.
        #
        # Nicht Python-round() verwenden, da dieses bei exakt halben Werten
        # Banker's Rounding verwendet:
        # round(0.5) == 0, round(1.5) == 2 usw.
        degrees_per_led = 360.0 / ctx.led_count
        led_position = mapped_direction_deg / degrees_per_led
        center = int(math.floor(led_position + 0.5)) % ctx.led_count

        color = _parse_color(
            params.get("color"),
            0x00C066,
        )

        brightness = min(
            1.0,
            max(
                0.0,
                _parse_float(params.get("brightness"), 1.0),
            ),
        )

        if brightness < 1.0:
            color = scale_color(color, brightness)

        frame: list[int | None] = [None] * ctx.led_count
        frame[center] = color
        return frame
