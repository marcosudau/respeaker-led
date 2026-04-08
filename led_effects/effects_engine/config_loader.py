"""Load effect definitions from dict / JSON / YAML."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .effects import (
    AlternateColorEffect,
    BlinkEffect,
    BreathEffect,
    DoaEffect,
    FadeEffect,
    LedEffect,
    OffEffect,
    RainbowEffect,
    SequenceEffect,
    StaticColorEffect,
)
from .advanced_effects import (
    CustomDoaEffect,
    TimerCountdownEffect,
    ProgressRingEffect,
    SpinnerEffect,
    PulseWaveEffect,
    SegmentMeterEffect,
)
from .rgb import NAMED_COLORS, RGB


# ============================================================
# Colour parsing (multiple formats)
# ============================================================

def parse_color(value: Any) -> RGB:
    """Parse a colour from various representations.

    Supported formats:
    - ``RGB`` instance (returned as-is)
    - ``list`` / ``tuple`` of three ints, e.g. ``[255, 0, 0]``
    - Hex string: ``"#FF0000"`` or ``"0xFF0000"``
    - Named string: ``"red"``, ``"soft_green"`` etc.
    """
    if isinstance(value, RGB):
        return value
    if isinstance(value, (list, tuple)):
        return RGB.from_tuple(value)
    if isinstance(value, str):
        lower = value.strip().lower().replace("-", "_")
        if lower in NAMED_COLORS:
            return NAMED_COLORS[lower]
        return RGB.from_hex(value)
    raise ValueError(f"Cannot parse color: {value!r}")


# ============================================================
# Single-effect spec → LedEffect
# ============================================================

def _get_float(spec: dict, key: str, default: float) -> float:
    return float(spec.get(key, default))


def _get_int(spec: dict, key: str, default: int) -> int:
    return int(spec.get(key, default))


def _get_bool(spec: dict, key: str, default: bool) -> bool:
    return bool(spec.get(key, default))


def _get_optional_int(spec: dict, key: str) -> int | None:
    value = spec.get(key)
    return None if value is None else int(value)


def _build_off(spec: dict) -> OffEffect:
    return OffEffect(hold_seconds=_get_float(spec, "hold_seconds", 0.0))


def _build_static(spec: dict) -> StaticColorEffect:
    return StaticColorEffect(
        color=parse_color(spec["color"]),
        hold_seconds=_get_float(spec, "hold_seconds", 0.0),
        persistent=_get_bool(spec, "persistent", False),
    )


def _build_breath(spec: dict) -> BreathEffect:
    return BreathEffect(
        color=parse_color(spec["color"]),
        speed=_get_int(spec, "speed", 1),
        brightness=_get_int(spec, "brightness", 128),
        hold_seconds=_get_float(spec, "hold_seconds", 0.0),
        persistent=_get_bool(spec, "persistent", False),
    )


def _build_rainbow(spec: dict) -> RainbowEffect:
    return RainbowEffect(
        speed=_get_int(spec, "speed", 1),
        brightness=_get_int(spec, "brightness", 128),
        hold_seconds=_get_float(spec, "hold_seconds", 0.0),
        persistent=_get_bool(spec, "persistent", False),
    )


def _build_blink(spec: dict) -> BlinkEffect:
    return BlinkEffect(
        color=parse_color(spec["color"]),
        on_seconds=_get_float(spec, "on_seconds", 0.15),
        off_seconds=_get_float(spec, "off_seconds", 0.15),
        repeat=_get_optional_int(spec, "repeat"),
    )


def _build_alternate(spec: dict) -> AlternateColorEffect:
    raw_colors = spec.get("colors", [])
    return AlternateColorEffect(
        colors=[parse_color(c) for c in raw_colors],
        interval_seconds=_get_float(spec, "interval_seconds", 0.3),
        repeat=_get_optional_int(spec, "repeat"),
    )


def _build_doa(spec: dict) -> DoaEffect:
    return DoaEffect(
        base_color=parse_color(spec["base_color"]),
        doa_color=parse_color(spec["doa_color"]),
        hold_seconds=_get_float(spec, "hold_seconds", 0.0),
        persistent=_get_bool(spec, "persistent", False),
    )


def _build_fade(spec: dict) -> FadeEffect:
    return FadeEffect(
        from_color=parse_color(spec["from_color"]),
        to_color=parse_color(spec["to_color"]),
        duration=_get_float(spec, "duration", 1.0),
        steps=_get_int(spec, "steps", 20),
    )


def _build_sequence(spec: dict) -> SequenceEffect:
    raw_effects = spec.get("effects", [])
    return SequenceEffect(
        effects=[parse_effect_spec(s) for s in raw_effects],
        repeat=_get_int(spec, "repeat", 1),
    )


def _build_custom_doa(spec: dict) -> CustomDoaEffect:
    return CustomDoaEffect(
        direction_deg=_get_float(spec, "direction_deg", 0.0),
        center_color=parse_color(spec.get("center_color", "cyan")),
        wing_color=parse_color(spec.get("wing_color", "soft_blue")),
        base_color=parse_color(spec.get("base_color", "black")),
        refresh_interval=_get_float(spec, "refresh_interval", 0.05),
    )


def _build_timer(spec: dict) -> TimerCountdownEffect:
    kw: dict[str, Any] = {
        "total_seconds": _get_float(spec, "total_seconds", 60.0),
        "brightness_steps": _get_int(spec, "brightness_steps", 8),
        "tick_flash": _get_bool(spec, "tick_flash", True),
    }
    for key in ("color", "warn_color", "critical_color", "background"):
        if key in spec:
            kw[key] = parse_color(spec[key])
    if "on_complete" in spec:
        kw["on_complete"] = str(spec["on_complete"])
    return TimerCountdownEffect(**kw)


def _build_progress(spec: dict) -> ProgressRingEffect:
    kw: dict[str, Any] = {
        "brightness_steps": _get_int(spec, "brightness_steps", 8),
        "refresh_interval": _get_float(spec, "refresh_interval", 0.04),
        "clockwise": _get_bool(spec, "clockwise", True),
    }
    for key in ("color", "tip_color", "background"):
        if key in spec:
            kw[key] = parse_color(spec[key])
    return ProgressRingEffect(**kw)


def _build_spinner(spec: dict) -> SpinnerEffect:
    kw: dict[str, Any] = {
        "dot_count": _get_int(spec, "dot_count", 1),
        "tail_length": _get_int(spec, "tail_length", 2),
        "period": _get_float(spec, "period", 1.2),
        "clockwise": _get_bool(spec, "clockwise", True),
    }
    for key in ("color", "tail_color", "background"):
        if key in spec:
            kw[key] = parse_color(spec[key])
    return SpinnerEffect(**kw)


def _build_pulse_wave(spec: dict) -> PulseWaveEffect:
    kw: dict[str, Any] = {
        "period": _get_float(spec, "period", 2.0),
        "width": _get_float(spec, "width", 3.0),
        "min_brightness": _get_float(spec, "min_brightness", 0.05),
    }
    for key in ("color", "background"):
        if key in spec:
            kw[key] = parse_color(spec[key])
    return PulseWaveEffect(**kw)


def _build_segment_meter(spec: dict) -> SegmentMeterEffect:
    kw: dict[str, Any] = {
        "refresh_interval": _get_float(spec, "refresh_interval", 0.05),
    }
    for key in ("low_color", "mid_color", "high_color", "background"):
        if key in spec:
            kw[key] = parse_color(spec[key])
    return SegmentMeterEffect(**kw)


_EFFECT_BUILDERS: dict[str, Any] = {
    "off": _build_off,
    "static": _build_static,
    "breath": _build_breath,
    "rainbow": _build_rainbow,
    "blink": _build_blink,
    "alternate": _build_alternate,
    "doa": _build_doa,
    "fade": _build_fade,
    "sequence": _build_sequence,
    "custom_doa": _build_custom_doa,
    "timer": _build_timer,
    "progress": _build_progress,
    "spinner": _build_spinner,
    "pulse_wave": _build_pulse_wave,
    "segment_meter": _build_segment_meter,
}


def parse_effect_spec(spec: dict) -> LedEffect:
    """Convert a dict specification into an ``LedEffect`` instance."""
    effect_type = str(spec.get("type", "")).strip().lower()
    builder = _EFFECT_BUILDERS.get(effect_type)
    if builder is None:
        available = ", ".join(sorted(_EFFECT_BUILDERS))
        raise ValueError(
            f"Unknown effect type '{effect_type}'. Available: {available}"
        )
    return builder(spec)


# ============================================================
# Bulk loaders
# ============================================================

def load_effects_from_dict(data: dict[str, dict]) -> dict[str, LedEffect]:
    """Parse a mapping of ``{name: spec_dict}`` into effects."""
    return {name: parse_effect_spec(spec) for name, spec in data.items()}


def load_effects_from_json(source: str | Path) -> dict[str, LedEffect]:
    """Load effects from a JSON file or JSON string.

    If *source* is a ``Path`` or points to an existing file it is read;
    otherwise it is parsed directly as a JSON string.
    """
    path = Path(source) if not isinstance(source, Path) else source
    if path.is_file():
        text = path.read_text(encoding="utf-8")
    else:
        text = str(source)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be a mapping of effect names to specs")
    return load_effects_from_dict(data)


def load_effects_from_yaml(source: str | Path) -> dict[str, LedEffect]:
    """Load effects from a YAML file or YAML string.

    Requires **PyYAML** (``pip install pyyaml``).
    """
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        raise ImportError(
            "PyYAML is required for YAML support. Install with: pip install pyyaml"
        ) from None

    path = Path(source) if not isinstance(source, Path) else source
    if path.is_file():
        text = path.read_text(encoding="utf-8")
    else:
        text = str(source)
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping of effect names to specs")
    return load_effects_from_dict(data)
