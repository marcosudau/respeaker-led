from __future__ import annotations

import pytest

from src.core.effect_schema import (
    DefinitionType,
    EffectDefinition,
    EffectParamDefinition,
    LayerId,
    LayerRule,
    OverlayMode,
    PlaybackMode,
)
from src.core.parameter_validation import (
    ParameterValidationError,
    normalize_runtime_inputs,
    resolve_configuration,
)


def make_definition() -> EffectDefinition:
    return EffectDefinition(
        id="test_overlay",
        title="Test Overlay",
        description="Test",
        definition_type=DefinitionType.OVERLAY,
        overlay_mode=OverlayMode.CONTROLLED,
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#000000"),
            "brightness": EffectParamDefinition(
                name="brightness",
                type="float",
                default=1.0,
                minimum=0.0,
                maximum=1.0,
            ),
        },
        runtime_input_schema={
            "level": EffectParamDefinition(
                name="level",
                type="float",
                minimum=0.0,
                maximum=100.0,
                aliases=("value",),
            ),
        },
        defaults={"color": "#000000", "brightness": 1.0},
        layer_rules={
            LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.PERSISTENT,),
                requires_indefinite_duration=True,
            )
        },
    )


def test_configuration_resolves_defaults_preset_and_overrides_to_canonical_values():
    resolved = resolve_configuration(
        make_definition(),
        preset={"color": "rot", "brightness": "50%"},
        overrides={"color": "green"},
    )

    assert resolved == {"color": "#00FF00", "brightness": 0.5}


def test_configuration_rejects_unknown_fields_with_suggestions():
    with pytest.raises(ParameterValidationError) as exc_info:
        resolve_configuration(make_definition(), overrides={"brightnes": 0.5})

    issue = exc_info.value.issues[0]
    assert issue.code == "unknown_field"
    assert issue.field == "config.brightnes"
    assert issue.suggestions == ("brightness",)


def test_runtime_inputs_are_validated_separately_from_configuration():
    assert normalize_runtime_inputs(make_definition(), {"level": "42"}) == {"level": 42.0}

    with pytest.raises(ParameterValidationError) as exc_info:
        normalize_runtime_inputs(make_definition(), {"color": "red"})

    assert exc_info.value.issues[0].field == "inputs.color"


def test_declared_input_alias_is_canonicalized_and_conflicts_are_rejected():
    assert normalize_runtime_inputs(make_definition(), {"value": "42%"}) == {
        "level": 42.0
    }

    with pytest.raises(ParameterValidationError) as exc_info:
        normalize_runtime_inputs(
            make_definition(),
            {"level": 10, "value": 20},
        )

    assert [issue.code for issue in exc_info.value.issues] == ["conflicting_fields"]


def test_gradient_and_random_color_range_use_strict_structures():
    gradient = EffectParamDefinition(name="gradient", type="gradient")
    color_range = EffectParamDefinition(name="color_range", type="color_range")
    definition = make_definition()
    definition.parameter_schema.update(
        {
            "gradient": gradient,
            "color_range": color_range,
        }
    )

    resolved = resolve_configuration(
        definition,
        overrides={
            "gradient": [
                {"at": 0, "color": "rot"},
                {"at": 1, "color": "blau"},
            ],
            "color_range": {
                "hue": [20, 80],
                "saturation": [0.5, 1],
                "brightness": [0.25, 0.9],
            },
        },
    )

    assert resolved["gradient"] == [
        {"at": 0.0, "color": "#FF0000"},
        {"at": 1.0, "color": "#0000FF"},
    ]
    assert resolved["color_range"]["hue"] == [20.0, 80.0]

    with pytest.raises(ParameterValidationError, match="sorted"):
        resolve_configuration(
            definition,
            overrides={
                "gradient": [
                    {"at": 1, "color": "red"},
                    {"at": 0, "color": "blue"},
                ]
            },
        )
