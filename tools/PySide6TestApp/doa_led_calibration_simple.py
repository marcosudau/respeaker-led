from __future__ import annotations

import importlib.util
import json
import math
import time
from pathlib import Path
from typing import Any

import msvcrt


VID = 0x2886
PID = 0x001A
LED_COUNT = 12
COLOR = 0x00FF66
OUTPUT_FILE = Path("doa_calibration.json")


def load_xvf_host() -> Any:
    script_path = Path(__file__).resolve()

    candidates = [
        script_path.parent.parent / "src" / "python_control" / "xvf_host.py",
        Path.cwd() / "src" / "python_control" / "xvf_host.py",
    ]

    for path in candidates:
        if not path.is_file():
            continue

        spec = importlib.util.spec_from_file_location("xvf_host", path)
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    raise FileNotFoundError(
        "src/python_control/xvf_host.py wurde nicht gefunden.\n"
        "Lege dieses Skript unter tools/ ab und starte es aus dem Projekt-Root."
    )


def scale_color(color: int, factor: float) -> int:
    factor = max(0.0, min(1.0, factor))
    red = int(((color >> 16) & 0xFF) * factor)
    green = int(((color >> 8) & 0xFF) * factor)
    blue = int((color & 0xFF) * factor)
    return (red << 16) | (green << 8) | blue


def show_position(device: Any, position_15deg: int) -> None:
    """
    Zeigt eine von 24 Positionen:
    - gerade Position: eine LED
    - ungerade Position: genau zwischen zwei LEDs
    """
    position_15deg %= LED_COUNT * 2
    frame = [0] * LED_COUNT

    lower_led = (position_15deg // 2) % LED_COUNT

    if position_15deg % 2 == 0:
        frame[lower_led] = COLOR
    else:
        upper_led = (lower_led + 1) % LED_COUNT
        half_color = scale_color(COLOR, 0.5)
        frame[lower_led] = half_color
        frame[upper_led] = half_color

    device.write("LED_EFFECT", [5])
    device.write("LED_RING_COLOR", frame)


def circular_mean(angles: list[float]) -> float:
    x = sum(math.cos(math.radians(angle)) for angle in angles)
    y = sum(math.sin(math.radians(angle)) for angle in angles)
    return math.degrees(math.atan2(y, x)) % 360.0


def signed_angle(value: float) -> float:
    result = (value + 180.0) % 360.0 - 180.0
    return 0.0 if abs(result) < 0.0001 else result


def record_direction(device: Any, text: str) -> float:
    print()
    input(f"{text}\nDrücke Enter und sprich danach etwa zwei Sekunden weiter ... ")

    # Während der Messung den eingebauten DoA-Modus verwenden.
    # So bleibt DOA_VALUE auch bei Firmwareständen zuverlässig aktiv,
    # bei denen es im frei steuerbaren Ringmodus einfrieren kann.
    device.write("LED_EFFECT", [4])

    print("3 ...")
    time.sleep(0.7)
    print("2 ...")
    time.sleep(0.7)
    print("1 ... jetzt sprechen!")

    values: list[float] = []
    end_time = time.monotonic() + 2.5

    while time.monotonic() < end_time:
        doa = device.read("DOA_VALUE")

        if isinstance(doa, tuple) and len(doa) == 2:
            angle = float(doa[0])
            vad_active = bool(int(doa[1]))

            if vad_active and 0.0 <= angle < 360.0:
                values.append(angle)

        time.sleep(0.05)

    if len(values) < 5:
        raise RuntimeError(
            "Es wurden zu wenige Sprachwerte erkannt. "
            "Bitte etwas lauter sprechen und das Skript erneut starten."
        )

    result = circular_mean(values)
    print(f"Messung abgeschlossen: {result:.1f}°")
    return result


def choose_main_speaking_position(device: Any) -> int:
    print(
        "\nSCHRITT 2\n"
        "Jetzt wird eine grüne Markierung angezeigt.\n"
        "Bleib an deiner normalen Sprechposition sitzen.\n\n"
        "A = Markierung 15° nach links\n"
        "D = Markierung 15° nach rechts\n"
        "Enter = Position stimmt\n"
    )

    position = 0
    show_position(device, position)

    while True:
        key = msvcrt.getwch().lower()

        if key == "a":
            position = (position - 1) % (LED_COUNT * 2)
            show_position(device, position)
        elif key == "d":
            position = (position + 1) % (LED_COUNT * 2)
            show_position(device, position)
        elif key == "\r":
            return position


def ask_positive_direction(device: Any, main_position: int) -> bool:
    show_position(device, main_position)
    time.sleep(0.5)
    show_position(device, main_position + 1)

    print(
        "\nSCHRITT 3\n"
        "Die Markierung wurde gerade um 15° weitergeschoben.\n"
        "Ist sie dabei von deiner Hauptsprechrichtung aus nach RECHTS gewandert?"
    )

    while True:
        answer = input("[J]a / [N]ein: ").strip().lower()

        if answer in {"j", "ja"}:
            show_position(device, main_position)
            return True

        if answer in {"n", "nein"}:
            show_position(device, main_position)
            return False


def calculate_result(
    raw_main_deg: float,
    raw_right_deg: float,
    target_main_deg: float,
    mapped_positive_is_right: bool,
) -> tuple[float, bool]:
    raw_movement = signed_angle(raw_right_deg - raw_main_deg)

    if abs(raw_movement) < 15.0:
        raise RuntimeError(
            "Die zweite Messposition war nicht weit genug rechts. "
            "Bitte das Skript erneut starten und deutlich weiter nach rechts gehen."
        )

    raw_positive_is_right = raw_movement > 0.0
    reverse = raw_positive_is_right != mapped_positive_is_right

    signed_raw_main = -raw_main_deg if reverse else raw_main_deg
    offset = signed_angle(target_main_deg - signed_raw_main)

    return offset, reverse


def main() -> int:
    print("Einfache ReSpeaker-DoA-Kalibrierung")
    print("===================================")
    print("Bitte LED-Dienst und Test-App vorher schließen.")

    xvf_host = load_xvf_host()
    device = xvf_host.find(vid=VID, pid=PID)

    if not device:
        print("\nKein ReSpeaker gefunden.")
        return 1

    original_effect = None
    original_ring = None

    try:
        try:
            original_effect = device.read("LED_EFFECT")
            original_ring = device.read("LED_RING_COLOR")
        except Exception:
            pass

        raw_main = record_direction(
            device,
            "SCHRITT 1\n"
            "Setz dich an deine normale Hauptsprechposition.",
        )

        main_position = choose_main_speaking_position(device)
        mapped_positive_is_right = ask_positive_direction(device, main_position)

        raw_right = record_direction(
            device,
            "SCHRITT 4\n"
            "Geh jetzt deutlich nach rechts neben deine Hauptsprechposition.",
        )

        target_main_deg = main_position * 15.0

        offset, reverse = calculate_result(
            raw_main_deg=raw_main,
            raw_right_deg=raw_right,
            target_main_deg=target_main_deg,
            mapped_positive_is_right=mapped_positive_is_right,
        )

        result = {
            "angle_offset_deg": round(offset, 1),
            "reverse": reverse,
        }

        OUTPUT_FILE.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        print("\nFERTIG")
        print("======")
        print("Diese Werte in den DoA-Effekt übernehmen:\n")
        print(f"angle_offset_deg: {result['angle_offset_deg']}")
        print(f"reverse: {'true' if result['reverse'] else 'false'}")
        print(f"\nGespeichert in: {OUTPUT_FILE.resolve()}")

        input("\nEnter drücken zum Beenden ... ")
        return 0

    finally:
        try:
            if original_ring is not None:
                device.write("LED_EFFECT", [5])
                device.write("LED_RING_COLOR", list(original_ring))

            if original_effect is not None:
                device.write("LED_EFFECT", list(original_effect))
        except Exception:
            pass

        try:
            device.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
'''

updated_effect = r'''from __future__ import annotations

import math
from typing import Any

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
            "Zeigt bei aktiver Voice Activity die erkannte Richtung weich "
            "zwischen den benachbarten LEDs an."
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

        raw_direction_deg = _parse_float(direction, 0.0) % 360.0

        if bool(params.get("reverse", False)):
            raw_direction_deg = (-raw_direction_deg) % 360.0

        angle_offset_deg = _parse_float(
            params.get("angle_offset_deg"),
            0.0,
        )

        direction_deg = (
            raw_direction_deg + angle_offset_deg
        ) % 360.0

        base_color = _parse_color(
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

        degrees_per_led = 360.0 / ctx.led_count
        led_position = direction_deg / degrees_per_led

        left_index = int(math.floor(led_position)) % ctx.led_count
        right_index = (left_index + 1) % ctx.led_count
        right_weight = led_position - math.floor(led_position)
        left_weight = 1.0 - right_weight

        frame: list[int | None] = [None] * ctx.led_count

        if left_weight > 0.0:
            frame[left_index] = scale_color(
                base_color,
                brightness * left_weight,
            )

        if right_weight > 0.0:
            frame[right_index] = scale_color(
                base_color,
                brightness * right_weight,
            )

        return frame