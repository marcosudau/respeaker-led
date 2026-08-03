from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

try:
    import msvcrt
except ImportError:  # pragma: no cover - das Skript ist primär für Windows gedacht
    msvcrt = None


LED_COUNT = 12
DEFAULT_COLOR = 0x00FF66
DEFAULT_INTERVAL_MS = 100


def parse_int(value: str) -> int:
    """Akzeptiert Dezimalwerte sowie 0x-/Hex-Werte."""
    return int(value, 0)


def scale_color(color: int, brightness: float) -> int:
    brightness = max(0.0, min(1.0, brightness))
    red = int(((color >> 16) & 0xFF) * brightness)
    green = int(((color >> 8) & 0xFF) * brightness)
    blue = int((color & 0xFF) * brightness)
    return (red << 16) | (green << 8) | blue


def candidate_xvf_paths(explicit: Path | None) -> list[Path]:
    candidates: list[Path] = []

    if explicit is not None:
        candidates.append(explicit)

    script_dir = Path(__file__).resolve().parent
    cwd = Path.cwd().resolve()

    for base in (script_dir, cwd):
        candidates.extend(
            [
                base / "src" / "python_control" / "xvf_host.py",
                base.parent / "src" / "python_control" / "xvf_host.py",
                base / "python_control" / "xvf_host.py",
            ]
        )

    # Doppelte Einträge entfernen, Reihenfolge beibehalten.
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.expanduser().resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def find_xvf_host(explicit: Path | None) -> Path:
    candidates = candidate_xvf_paths(explicit)
    for path in candidates:
        if path.is_file():
            return path

    attempted = "\n".join(f"  - {path}" for path in candidates)
    raise FileNotFoundError(
        "xvf_host.py wurde nicht gefunden.\n"
        "Lege dieses Skript in den Projekt-Root oder in tools/, "
        "oder übergib --xvf-host.\n"
        f"Geprüfte Pfade:\n{attempted}"
    )


def load_xvf_host(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("xvf_host_calibration", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"xvf_host.py konnte nicht geladen werden: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_offset(value: float) -> float:
    """Offset für eine gut lesbare Anzeige auf [-180, 180) normalisieren."""
    normalized = (value + 180.0) % 360.0 - 180.0
    # -0.0 vermeiden
    return 0.0 if abs(normalized) < 1e-9 else normalized


def map_direction(raw_direction_deg: float, reverse: bool, offset_deg: float) -> float:
    """
    Korrekte Reihenfolge:
    1. Rohwinkel optional spiegeln
    2. festen Hardware-Offset addieren
    3. auf 0..359 normalisieren
    """
    direction = (-raw_direction_deg) if reverse else raw_direction_deg
    return (direction + offset_deg) % 360.0


def angle_to_led_index(direction_deg: float, led_count: int = LED_COUNT) -> int:
    """
    Eindeutige Rundung auf die nächstgelegene LED.
    Kein Python-round(), da dieses Banker's Rounding verwendet.
    """
    degrees_per_led = 360.0 / led_count
    position = (direction_deg % 360.0) / degrees_per_led
    return int(math.floor(position + 0.5)) % led_count


def make_single_led_frame(index: int, color: int, led_count: int = LED_COUNT) -> list[int]:
    frame = [0] * led_count
    frame[index % led_count] = color
    return frame


def clear_status_line() -> None:
    print("\r" + (" " * 140) + "\r", end="", flush=True)


def print_help() -> None:
    print(
        """
ReSpeaker DoA-/LED-Kalibrierung
===============================

Modi:
  i       LED-Indexmodus: einzelne LED manuell auswählen
  t       Custom-Tracking: DOA_VALUE mit reverse/offset auf LED_RING_COLOR abbilden
  n       Nativer Firmware-DoA-Modus (LED_EFFECT=4) zum Gegenvergleich

Kalibrierung:
  ← / →   Offset um -1° / +1°
  ↓ / ↑   Offset um -30° / +30°
  r       Drehrichtung spiegeln (reverse)
  v       VAD-Gating ein/aus
  s       Kalibrierung als JSON speichern

LED-Indexmodus:
  0..9    LED-Index 0..9 einschalten
  a       LED-Index 10 einschalten
  b       LED-Index 11 einschalten
  - / +   vorherige / nächste LED

Allgemein:
  h       Hilfe erneut anzeigen
  q       Beenden und ursprünglichen LED-Zustand wiederherstellen

Empfohlener Ablauf:
  1. Mit i sowie 0, 1, 2 ... die physische Lage und Laufrichtung der Indizes prüfen.
  2. Mit t in das Custom-Tracking wechseln.
  3. Aus einer bekannten Richtung sprechen und den Offset einstellen.
  4. Die Quelle um etwa 90° versetzen. Läuft die LED falsch herum, r drücken.
  5. Offset nochmals fein korrigieren und mit s speichern.

Hinweis:
  Falls DOA_VALUE im Custom-Tracking feststeht, mit n prüfen, ob es im nativen
  DoA-Modus weiterläuft. Dann liegt wahrscheinlich eine Firmwarekopplung zwischen
  DOA_VALUE und LED_EFFECT vor.
"""
    )


def read_key() -> str | None:
    if msvcrt is None:
        return None
    if not msvcrt.kbhit():
        return None

    key = msvcrt.getwch()

    # Windows-Sondertasten bestehen aus Präfix + Scan-Code.
    if key in ("\x00", "\xe0"):
        code = msvcrt.getwch()
        return {
            "K": "LEFT",
            "M": "RIGHT",
            "H": "UP",
            "P": "DOWN",
        }.get(code)

    return key.lower()


def save_calibration(path: Path, offset_deg: float, reverse: bool) -> None:
    payload = {
        "angle_offset_deg": normalize_offset(offset_deg),
        "reverse": reverse,
        "led_count": LED_COUNT,
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Unabhängige ReSpeaker-XVF3800-DoA-/LED-Kalibrierung."
    )
    parser.add_argument(
        "--xvf-host",
        type=Path,
        default=None,
        help="Expliziter Pfad zu src/python_control/xvf_host.py",
    )
    parser.add_argument("--vid", type=parse_int, default=0x2886)
    parser.add_argument("--pid", type=parse_int, default=0x001A)
    parser.add_argument(
        "--interval-ms",
        type=int,
        default=DEFAULT_INTERVAL_MS,
        help="Abfrageintervall, Standard: 100 ms (10 Hz)",
    )
    parser.add_argument(
        "--color",
        type=parse_int,
        default=DEFAULT_COLOR,
        help="Kalibrierfarbe als 0xRRGGBB, Standard: 0x00FF66",
    )
    parser.add_argument(
        "--brightness",
        type=float,
        default=0.35,
        help="Helligkeitsfaktor 0.0..1.0, Standard: 0.35",
    )
    parser.add_argument(
        "--offset",
        type=float,
        default=0.0,
        help="Initialer Winkeloffset in Grad",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Initial mit gespiegelter Drehrichtung starten",
    )
    parser.add_argument(
        "--no-vad-gate",
        action="store_true",
        help="Richtungs-LED auch bei VAD=0 anzeigen",
    )
    parser.add_argument(
        "--save-file",
        type=Path,
        default=Path("doa_calibration.json"),
        help="Zieldatei für Taste s",
    )
    args = parser.parse_args()

    if msvcrt is None:
        print("Dieses interaktive Skript benötigt unter Windows das Modul msvcrt.")
        return 2

    if args.interval_ms < 20:
        parser.error("--interval-ms muss mindestens 20 sein.")
    if not 0.0 <= args.brightness <= 1.0:
        parser.error("--brightness muss zwischen 0.0 und 1.0 liegen.")

    xvf_path = find_xvf_host(args.xvf_host)
    print(f"xvf_host.py: {xvf_path}")

    module = load_xvf_host(xvf_path)
    device = module.find(vid=args.vid, pid=args.pid)
    if not device:
        print(
            "Kein ReSpeaker gefunden. Beende zuerst LED-Dienst/Test-App, "
            "falls diese das USB-Gerät geöffnet hält."
        )
        return 1

    original_effect: tuple[int, ...] | None = None
    original_ring: tuple[int, ...] | None = None

    try:
        try:
            version = device.read("VERSION")
            print("Firmware:", ".".join(str(int(v)) for v in version))
        except Exception as exc:
            print(f"Firmwareversion konnte nicht gelesen werden: {exc}")

        try:
            original_effect = tuple(int(v) for v in device.read("LED_EFFECT"))
        except Exception:
            original_effect = None

        try:
            original_ring = tuple(int(v) for v in device.read("LED_RING_COLOR"))
        except Exception:
            original_ring = None

        mode = "index"
        selected_index = 0
        reverse = bool(args.reverse)
        offset_deg = normalize_offset(float(args.offset))
        vad_gate = not args.no_vad_gate
        color = scale_color(args.color & 0xFFFFFF, args.brightness)
        interval_s = args.interval_ms / 1000.0

        last_written_frame: tuple[int, ...] | None = None
        last_effect_mode: int | None = None
        last_direction: float | None = None
        last_vad: bool | None = None
        last_error: str | None = None

        def set_effect_mode(effect_mode: int) -> None:
            nonlocal last_effect_mode
            if last_effect_mode == effect_mode:
                return
            device.write("LED_EFFECT", [effect_mode])
            last_effect_mode = effect_mode

        def write_frame(frame: list[int]) -> None:
            nonlocal last_written_frame
            encoded = tuple(frame)
            if encoded == last_written_frame:
                return
            set_effect_mode(5)
            device.write("LED_RING_COLOR", frame)
            last_written_frame = encoded

        print_help()
        print("Startmodus: LED-Indexmodus, Index 0")
        write_frame(make_single_led_frame(selected_index, color))

        running = True
        next_tick = time.perf_counter()

        while running:
            key = read_key()

            if key is not None:
                clear_status_line()

                if key == "q":
                    running = False
                    continue
                if key == "h":
                    print_help()
                elif key == "i":
                    mode = "index"
                    write_frame(make_single_led_frame(selected_index, color))
                elif key == "t":
                    mode = "tracking"
                    # Beim nächsten Tick wird der Tracking-Frame geschrieben.
                    last_written_frame = None
                elif key == "n":
                    mode = "native"
                    set_effect_mode(4)
                    last_written_frame = None
                elif key == "r":
                    reverse = not reverse
                    last_written_frame = None
                elif key == "v":
                    vad_gate = not vad_gate
                    last_written_frame = None
                elif key == "LEFT":
                    offset_deg = normalize_offset(offset_deg - 1.0)
                    last_written_frame = None
                elif key == "RIGHT":
                    offset_deg = normalize_offset(offset_deg + 1.0)
                    last_written_frame = None
                elif key == "DOWN":
                    offset_deg = normalize_offset(offset_deg - 30.0)
                    last_written_frame = None
                elif key == "UP":
                    offset_deg = normalize_offset(offset_deg + 30.0)
                    last_written_frame = None
                elif key == "-":
                    selected_index = (selected_index - 1) % LED_COUNT
                    if mode == "index":
                        write_frame(make_single_led_frame(selected_index, color))
                elif key in ("+", "="):
                    selected_index = (selected_index + 1) % LED_COUNT
                    if mode == "index":
                        write_frame(make_single_led_frame(selected_index, color))
                elif key in "0123456789":
                    selected_index = int(key)
                    mode = "index"
                    write_frame(make_single_led_frame(selected_index, color))
                elif key == "a":
                    selected_index = 10
                    mode = "index"
                    write_frame(make_single_led_frame(selected_index, color))
                elif key == "b":
                    selected_index = 11
                    mode = "index"
                    write_frame(make_single_led_frame(selected_index, color))
                elif key == "s":
                    save_path = args.save_file.expanduser().resolve()
                    save_calibration(save_path, offset_deg, reverse)
                    print(f"Gespeichert: {save_path}")
                    print(
                        "Preset-Werte:\n"
                        f"  angle_offset_deg: {normalize_offset(offset_deg):.1f}\n"
                        f"  reverse: {'true' if reverse else 'false'}"
                    )

            now = time.perf_counter()
            if now < next_tick:
                time.sleep(min(0.01, next_tick - now))
                continue
            next_tick = now + interval_s

            try:
                payload = device.read("DOA_VALUE")
                if not isinstance(payload, tuple) or len(payload) != 2:
                    raise RuntimeError(f"Unerwartetes DOA_VALUE: {payload!r}")

                raw_direction = float(payload[0])
                vad_active = bool(int(payload[1]))
                if not math.isfinite(raw_direction) or not 0.0 <= raw_direction < 360.0:
                    raise RuntimeError(f"Ungültiger DoA-Winkel: {raw_direction!r}")

                mapped_direction = map_direction(raw_direction, reverse, offset_deg)
                mapped_index = angle_to_led_index(mapped_direction)

                if mode == "tracking":
                    if vad_gate and not vad_active:
                        write_frame([0] * LED_COUNT)
                    else:
                        write_frame(make_single_led_frame(mapped_index, color))
                elif mode == "index":
                    # Frame nur erneut schreiben, falls ein anderer Modus ihn verändert hat.
                    write_frame(make_single_led_frame(selected_index, color))
                elif mode == "native":
                    set_effect_mode(4)

                last_direction = raw_direction
                last_vad = vad_active
                last_error = None

                mode_label = {
                    "index": f"INDEX {selected_index:02d}",
                    "tracking": "CUSTOM-TRACKING",
                    "native": "NATIVER DOA",
                }[mode]

                status = (
                    f"Modus={mode_label:<16} "
                    f"raw={raw_direction:6.1f}°  "
                    f"mapped={mapped_direction:6.1f}°  "
                    f"LED={mapped_index:02d}  "
                    f"VAD={'AN ' if vad_active else 'AUS'}  "
                    f"reverse={'AN ' if reverse else 'AUS'}  "
                    f"offset={offset_deg:+7.1f}°  "
                    f"VAD-Gate={'AN ' if vad_gate else 'AUS'}"
                )
                print("\r" + status.ljust(140), end="", flush=True)

            except Exception as exc:
                message = str(exc)
                if message != last_error:
                    clear_status_line()
                    print(f"Lesefehler: {message}")
                    last_error = message
                # Bei einem kurzen USB-Fehler nicht sofort abbrechen.
                time.sleep(0.05)

        clear_status_line()
        print("Beende Kalibrierung ...")

    finally:
        # Möglichst den Zustand wiederherstellen, der vor dem Skript aktiv war.
        try:
            if original_ring is not None:
                device.write("LED_EFFECT", [5])
                device.write("LED_RING_COLOR", list(original_ring))
            if original_effect is not None:
                device.write("LED_EFFECT", list(original_effect))
        except Exception as exc:
            print(f"Ursprünglicher LED-Zustand konnte nicht vollständig wiederhergestellt werden: {exc}")
        finally:
            device.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
