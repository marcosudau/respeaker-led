"""Effects Engine – reusable, parametrised LED effect toolkit.

Public API
----------
Colours & palette::

    from led_effects.effects_engine import RGB, Colors, NAMED_COLORS, parse_color

Effects (building blocks)::

    from led_effects.effects_engine import (
        LedEffect, OffEffect, StaticColorEffect, BreathEffect,
        RainbowEffect, BlinkEffect, AlternateColorEffect,
        FadeEffect, SequenceEffect, DoaEffect,
    )

Backend::

    from led_effects.effects_engine import (
        LedRingBackend, RecordingBackend, DryRunBackend, XvfHostBackend,
    )

Registry & loader::

    from led_effects.effects_engine import (
        EffectRegistry,
        parse_effect_spec, load_effects_from_dict,
        load_effects_from_json, load_effects_from_yaml,
    )

Controller::

    from led_effects.effects_engine import LedRingController

Standard library::

    from led_effects.effects_engine import build_standard_effects, build_standard_registry
"""
from __future__ import annotations

# -- colours
from .rgb import RGB, Colors, NAMED_COLORS

# -- backend
from .backend import (
    LED_COUNT,
    LedRingBackend,
    LedRingError,
    HostCommandError,
    RecordingBackend,
    RecordedCall,
    DryRunBackend,
    XvfHostBackend,
)

# -- context
from .context import EffectContext

# -- effects
from .effects import (
    LedEffect,
    OffEffect,
    StaticColorEffect,
    BreathEffect,
    RainbowEffect,
    DoaEffect,
    BlinkEffect,
    AlternateColorEffect,
    FadeEffect,
    SequenceEffect,
)

# -- registry
from .registry import EffectRegistry

# -- config loader
from .config_loader import (
    parse_color,
    parse_effect_spec,
    load_effects_from_dict,
    load_effects_from_json,
    load_effects_from_yaml,
)

# -- controller
from .controller import LedRingController

# -- advanced effects
from .advanced_effects import (
    CustomDoaEffect,
    TimerCountdownEffect,
    ProgressRingEffect,
    SpinnerEffect,
    PulseWaveEffect,
    SegmentMeterEffect,
)

# -- easy API
from .easy import EasyLedRing, easy_hardware, easy_preview

# -- standard library
from .stdlib import build_standard_effects, build_standard_registry

__all__ = [
    # colours
    "RGB",
    "Colors",
    "NAMED_COLORS",
    "parse_color",
    # backend
    "LED_COUNT",
    "LedRingBackend",
    "LedRingError",
    "HostCommandError",
    "RecordingBackend",
    "RecordedCall",
    "DryRunBackend",
    "XvfHostBackend",
    # context
    "EffectContext",
    # effects
    "LedEffect",
    "OffEffect",
    "StaticColorEffect",
    "BreathEffect",
    "RainbowEffect",
    "DoaEffect",
    "BlinkEffect",
    "AlternateColorEffect",
    "FadeEffect",
    "SequenceEffect",
    # advanced effects
    "CustomDoaEffect",
    "TimerCountdownEffect",
    "ProgressRingEffect",
    "SpinnerEffect",
    "PulseWaveEffect",
    "SegmentMeterEffect",
    # easy API
    "EasyLedRing",
    "easy_hardware",
    "easy_preview",
    # registry
    "EffectRegistry",
    # config loader
    "parse_effect_spec",
    "load_effects_from_dict",
    "load_effects_from_json",
    "load_effects_from_yaml",
    # controller
    "LedRingController",
    # stdlib
    "build_standard_effects",
    "build_standard_registry",
]
