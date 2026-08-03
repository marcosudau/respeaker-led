from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.core.effect_schema import EffectInvocation, LayerId, PlaybackMode, RenderContext
from src.core.parameter_validation import ParameterValidationError, normalize_runtime_inputs
from src.engine.effect_package_builder import (
    build_effect_package,
    build_effect_set,
    validate_effect_source,
    validate_effect_set_source,
)
from src.engine.effect_package_loader import load_effect_package, load_effect_set
from tools.effect_building.effect_set_sources import (
    discover_effect_sets,
    discover_effect_sources,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = PROJECT_ROOT / "docs" / "effect-development" / "templates"
EXAMPLE_ROOT = PROJECT_ROOT / "docs" / "effect_examples"

TEMPLATES = (
    "tpl_state_basic",
    "tpl_overlay_push",
    "tpl_overlay_pull",
    "tpl_overlay_timed",
    "tpl_event_basic",
)
EXAMPLES = {
    "example_rotation_state": EXAMPLE_ROOT / "states" / "example_rotation",
    "example_doa_overlay": EXAMPLE_ROOT / "overlays" / "example_doa",
    "example_short_pulse_event": EXAMPLE_ROOT / "events" / "example_short_pulse",
}


def _context(
    effect_class,
    *,
    layer: LayerId,
    now: float,
    inputs: dict | None = None,
    duration_ms: int | None = None,
) -> RenderContext:
    definition = effect_class.get_definition()
    return RenderContext(
        now=now,
        led_count=12,
        layer_id=layer,
        definition=definition,
        invocation=EffectInvocation(
            invocation_id=f"tutorial-{definition.id}",
            effect_id=definition.id,
            target_layer=layer,
            playback_mode=(
                PlaybackMode.SINGLE_RUN
                if layer in {LayerId.EVENT_LAYER, LayerId.TEMP_OVERLAY_LAYER}
                else PlaybackMode.LOOP
            ),
            requested_duration_ms=duration_ms,
            created_at=10.0,
        ),
        params=dict(definition.defaults),
        inputs=dict(inputs or {}),
    )


@pytest.mark.parametrize("template_name", TEMPLATES)
def test_tutorial_templates_are_valid_but_not_standard_sources(template_name):
    result = validate_effect_source(TEMPLATE_ROOT / template_name)

    assert result.kind == "effect_source"
    assert result.source_id == "tutorial-templates"


def test_tutorial_examples_build_load_and_render(tmp_path):
    loaded = {}
    for effect_id, source in EXAMPLES.items():
        output = tmp_path / f"{effect_id}.lefx"
        build_effect_package(source, output)
        loaded[effect_id] = load_effect_package(output)

    state = loaded["example_rotation_state"].effect_class()
    first = state.render(
        _context(state, layer=LayerId.STATE_LAYER, now=10.0)
    )
    later = state.render(
        _context(state, layer=LayerId.STATE_LAYER, now=10.5)
    )
    assert len(first) == 12
    assert first != later

    overlay_package = loaded["example_doa_overlay"]
    overlay = overlay_package.effect_class()
    empty = overlay.render(
        _context(overlay, layer=LayerId.ONGOING_OVERLAY_LAYER, now=10.0)
    )
    east = overlay.render(
        _context(
            overlay,
            layer=LayerId.ONGOING_OVERLAY_LAYER,
            now=10.0,
            inputs={"direction_deg": 90.0},
        )
    )
    assert empty == [None] * 12
    assert east.index(next(value for value in east if value is not None)) == 3
    with pytest.raises(ParameterValidationError):
        normalize_runtime_inputs(
            overlay_package.effect_class.get_definition(),
            {"unknown_direction": 90},
        )

    event = loaded["example_short_pulse_event"].effect_class()
    start = event.render(
        _context(event, layer=LayerId.EVENT_LAYER, now=10.0, duration_ms=600)
    )
    peak = event.render(
        _context(event, layer=LayerId.EVENT_LAYER, now=10.3, duration_ms=600)
    )
    end = event.render(
        _context(event, layer=LayerId.EVENT_LAYER, now=10.6, duration_ms=600)
    )
    assert start == [0] * 12
    assert peak != start
    assert end == [0] * 12


def test_tutorial_lefxset_is_built_from_prebuilt_packages(tmp_path):
    set_source = tmp_path / "tutorial-set"
    effects_root = set_source / "effects"
    effects_root.mkdir(parents=True)
    shutil.copy2(EXAMPLE_ROOT / "tutorial_set" / "set.yaml", set_source / "set.yaml")

    for effect_id, source in EXAMPLES.items():
        build_effect_package(source, effects_root / f"{effect_id}.lefx")

    validation = validate_effect_set_source(set_source)
    output = tmp_path / "tutorial-effects.lefxset"
    build_effect_set(set_source, output)
    loaded = load_effect_set(output)

    assert validation.warnings == ()
    assert {item.manifest.effect_id for item in loaded.effects} == set(EXAMPLES)


def test_tutorial_definitions_are_not_in_standard_catalog():
    default_set = next(
        effect_set
        for effect_set in discover_effect_sets()
        if effect_set.set_id == "default-effects"
    )
    standard_ids = {spec.effect_id for spec in discover_effect_sources(default_set)}

    assert standard_ids.isdisjoint(EXAMPLES)
