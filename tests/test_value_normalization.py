from __future__ import annotations

import pytest

from respeaker_led.core.value_normalization import (
    ValueNormalizationError,
    describe_color,
    format_color,
    parse_angle_degrees,
    parse_bool,
    parse_color,
    parse_duration_ms,
    parse_ratio,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("#00ff00", 0x00FF00),
        ("0x00FF00", 0x00FF00),
        ("green", 0x00FF00),
        ("gruen", 0x00FF00),
        ("gr\u00fcn", 0x00FF00),
        ("WEISS", 0xFFFFFF),
        ("wei\u00df", 0xFFFFFF),
        (0x123456, 0x123456),
    ],
)
def test_parse_color_accepts_canonical_and_named_aliases(value, expected):
    assert parse_color(value) == expected


def test_unknown_color_returns_machine_readable_suggestions():
    with pytest.raises(ValueNormalizationError) as exc_info:
        parse_color("gren")

    assert exc_info.value.code == "unknown_color"
    assert "green" in exc_info.value.suggestions
    assert exc_info.value.to_dict(field="config.color")["field"] == "config.color"


def test_color_output_is_canonical_and_names_exact_catalog_values():
    assert format_color("red") == "#FF0000"
    assert describe_color("#FF0000") == {"hex": "#FF0000", "name": "red", "aliases": ["rot"]}
    assert describe_color("#123456") == {"hex": "#123456"}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1500, 1500),
        ("1500ms", 1500),
        ("1.5s", 1500),
        ("0.25 s", 250),
    ],
)
def test_duration_normalization(value, expected):
    assert parse_duration_ms(value) == expected


@pytest.mark.parametrize(("value", "expected"), [(0.5, 0.5), ("0.5", 0.5), ("50%", 0.5)])
def test_ratio_normalization(value, expected):
    assert parse_ratio(value) == expected


def test_angle_and_boolean_normalization():
    assert parse_angle_degrees("450deg") == 90.0
    assert parse_bool("an") is True
    assert parse_bool("aus") is False
    assert parse_bool("ja") is True
    assert parse_bool("nein") is False
