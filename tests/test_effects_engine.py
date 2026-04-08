"""Comprehensive tests for the effects engine."""
from __future__ import annotations

import json
import tempfile
import threading
import time
from pathlib import Path

import pytest

from led_effects.effects_engine import (
    RGB,
    Colors,
    NAMED_COLORS,
    parse_color,
    LedRingBackend,
    RecordingBackend,
    DryRunBackend,
    EffectContext,
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
    EffectRegistry,
    parse_effect_spec,
    load_effects_from_dict,
    load_effects_from_json,
    LedRingController,
    build_standard_effects,
    build_standard_registry,
)


# ============================================================
# Helpers
# ============================================================

def make_ctx(backend: RecordingBackend | None = None) -> EffectContext:
    """Create a context with a RecordingBackend and an unset stop event."""
    return EffectContext(
        backend=backend or RecordingBackend(),
        stop_event=threading.Event(),
    )


# ============================================================
# RGB
# ============================================================


class TestRGB:
    def test_create_valid(self):
        c = RGB(10, 20, 30)
        assert c.r == 10 and c.g == 20 and c.b == 30

    def test_channel_boundaries(self):
        assert RGB(0, 0, 0) == Colors.BLACK
        assert RGB(255, 255, 255) == Colors.WHITE

    def test_negative_value_raises(self):
        with pytest.raises(ValueError):
            RGB(-1, 0, 0)

    def test_overflow_value_raises(self):
        with pytest.raises(ValueError):
            RGB(0, 256, 0)

    def test_non_int_raises(self):
        with pytest.raises(ValueError):
            RGB(1.5, 0, 0)  # type: ignore[arg-type]

    def test_to_hex(self):
        assert RGB(255, 0, 128).to_hex() == "#FF0080"

    def test_to_xvf_hex(self):
        assert RGB(255, 0, 128).to_xvf_hex() == "0xFF0080"

    def test_to_tuple(self):
        assert RGB(1, 2, 3).to_tuple() == (1, 2, 3)

    def test_scaled(self):
        c = RGB(200, 100, 50).scaled(0.5)
        assert c == RGB(100, 50, 25)

    def test_scaled_clamps(self):
        c = RGB(100, 100, 100).scaled(2.0)
        assert c == RGB(100, 100, 100)  # clamped to 1.0
        c2 = RGB(100, 100, 100).scaled(-1.0)
        assert c2 == RGB(0, 0, 0)  # clamped to 0.0

    def test_blend(self):
        a = RGB(0, 0, 0)
        b = RGB(200, 100, 50)
        mid = a.blend(b, 0.5)
        assert mid == RGB(100, 50, 25)

    def test_blend_extremes(self):
        a = RGB(10, 20, 30)
        b = RGB(100, 200, 250)
        assert a.blend(b, 0.0) == a
        assert a.blend(b, 1.0) == b

    def test_from_tuple(self):
        assert RGB.from_tuple([10, 20, 30]) == RGB(10, 20, 30)
        assert RGB.from_tuple((10, 20, 30)) == RGB(10, 20, 30)

    def test_from_tuple_wrong_length_raises(self):
        with pytest.raises(ValueError):
            RGB.from_tuple([1, 2])

    def test_from_hex_hash(self):
        assert RGB.from_hex("#FF8000") == RGB(255, 128, 0)

    def test_from_hex_0x(self):
        assert RGB.from_hex("0xFF8000") == RGB(255, 128, 0)

    def test_from_hex_plain(self):
        assert RGB.from_hex("FF8000") == RGB(255, 128, 0)

    def test_from_hex_invalid_raises(self):
        with pytest.raises(ValueError):
            RGB.from_hex("ZZZZZZ")

    def test_from_hex_short_raises(self):
        with pytest.raises(ValueError):
            RGB.from_hex("#FFF")

    def test_frozen(self):
        c = RGB(1, 2, 3)
        with pytest.raises(AttributeError):
            c.r = 5  # type: ignore[misc]


class TestColors:
    def test_named_colors_not_empty(self):
        assert len(NAMED_COLORS) >= 16

    def test_all_colors_are_rgb(self):
        for name, color in NAMED_COLORS.items():
            assert isinstance(color, RGB), f"{name} is not RGB"


class TestParseColor:
    def test_from_rgb_instance(self):
        c = RGB(1, 2, 3)
        assert parse_color(c) is c

    def test_from_list(self):
        assert parse_color([255, 0, 128]) == RGB(255, 0, 128)

    def test_from_tuple(self):
        assert parse_color((0, 255, 0)) == RGB(0, 255, 0)

    def test_from_named(self):
        assert parse_color("red") == Colors.RED

    def test_from_named_case_insensitive(self):
        assert parse_color("SOFT_GREEN") == Colors.SOFT_GREEN

    def test_from_hex(self):
        assert parse_color("#FF0000") == RGB(255, 0, 0)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_color(12345)


# ============================================================
# RecordingBackend
# ============================================================


class TestRecordingBackend:
    def test_records_off(self):
        b = RecordingBackend()
        b.off()
        assert b.method_names() == ["off"]

    def test_records_single_color(self):
        b = RecordingBackend()
        b.single_color(Colors.RED)
        assert b.calls[0].method == "single_color"
        assert b.calls[0].args == (Colors.RED,)

    def test_records_breath_with_kwargs(self):
        b = RecordingBackend()
        b.breath(Colors.BLUE, speed=3, brightness=200)
        assert b.calls[0].kwargs == {"speed": 3, "brightness": 200}

    def test_clear(self):
        b = RecordingBackend()
        b.off()
        b.off()
        b.clear()
        assert len(b.calls) == 0


# ============================================================
# DryRunBackend
# ============================================================


class TestDryRunBackend:
    def test_no_exception(self):
        b = DryRunBackend(logger=None)
        b.off()
        b.single_color(Colors.RED)
        b.breath(Colors.GREEN)
        b.rainbow()
        b.doa(Colors.BLUE, Colors.CYAN)
        b.power_led_ring(True)


# ============================================================
# EffectContext
# ============================================================


class TestEffectContext:
    def test_is_stopped_initially_false(self):
        ctx = make_ctx()
        assert not ctx.is_stopped

    def test_is_stopped_after_set(self):
        ctx = make_ctx()
        ctx.stop_event.set()
        assert ctx.is_stopped

    def test_sleep_returns_true_if_not_stopped(self):
        ctx = make_ctx()
        assert ctx.sleep(0.01) is True

    def test_sleep_returns_false_if_stopped(self):
        ctx = make_ctx()
        ctx.stop_event.set()
        assert ctx.sleep(10.0) is False


# ============================================================
# Effects
# ============================================================


class TestOffEffect:
    def test_calls_off(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        OffEffect().run(ctx)
        assert b.method_names() == ["off"]

    def test_holds(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        start = time.monotonic()
        OffEffect(hold_seconds=0.05).run(ctx)
        assert time.monotonic() - start >= 0.04


class TestStaticColorEffect:
    def test_calls_single_color(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        StaticColorEffect(Colors.RED).run(ctx)
        assert b.method_names() == ["single_color"]
        assert b.calls[0].args == (Colors.RED,)

    def test_persistent_blocks_until_stopped(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        done = threading.Event()

        def runner():
            StaticColorEffect(Colors.GREEN, persistent=True).run(ctx)
            done.set()

        t = threading.Thread(target=runner, daemon=True)
        t.start()
        time.sleep(0.05)
        assert not done.is_set()
        ctx.stop_event.set()
        done.wait(timeout=1.0)
        assert done.is_set()


class TestBreathEffect:
    def test_calls_breath(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        BreathEffect(Colors.CYAN, speed=2, brightness=100).run(ctx)
        assert "breath" in b.method_names()
        assert b.calls[0].kwargs == {"speed": 2, "brightness": 100}


class TestRainbowEffect:
    def test_calls_rainbow(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        RainbowEffect(speed=3, brightness=200).run(ctx)
        assert "rainbow" in b.method_names()


class TestDoaEffect:
    def test_calls_doa(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        DoaEffect(Colors.BLUE, Colors.YELLOW).run(ctx)
        assert "doa" in b.method_names()


class TestBlinkEffect:
    def test_finite_repeat(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        BlinkEffect(Colors.RED, on_seconds=0.01, off_seconds=0.01, repeat=2).run(ctx)
        assert b.method_names().count("single_color") == 2
        assert b.method_names().count("off") == 2

    def test_stops_on_signal(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        done = threading.Event()

        def runner():
            BlinkEffect(Colors.RED, on_seconds=0.02, off_seconds=0.02).run(ctx)
            done.set()

        t = threading.Thread(target=runner, daemon=True)
        t.start()
        time.sleep(0.1)
        ctx.stop_event.set()
        done.wait(timeout=1.0)
        assert done.is_set()


class TestAlternateColorEffect:
    def test_finite_repeat(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        AlternateColorEffect(
            colors=[Colors.RED, Colors.GREEN],
            interval_seconds=0.01,
            repeat=1,
        ).run(ctx)
        assert b.calls[0].args == (Colors.RED,)
        assert b.calls[1].args == (Colors.GREEN,)

    def test_empty_colors_returns(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        AlternateColorEffect(colors=[], repeat=1).run(ctx)
        assert len(b.calls) == 0


class TestFadeEffect:
    def test_produces_intermediate_colors(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        FadeEffect(Colors.BLACK, Colors.WHITE, duration=0.05, steps=4).run(ctx)
        colors = [c.args[0] for c in b.calls if c.method == "single_color"]
        assert len(colors) == 5  # 0, 0.25, 0.5, 0.75, 1.0
        assert colors[0] == Colors.BLACK
        assert colors[-1] == Colors.WHITE

    def test_intermediate_values(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        FadeEffect(
            RGB(0, 0, 0), RGB(100, 200, 100), duration=0.02, steps=2
        ).run(ctx)
        colors = [c.args[0] for c in b.calls if c.method == "single_color"]
        assert colors[1] == RGB(50, 100, 50)


class TestSequenceEffect:
    def test_runs_in_order(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        SequenceEffect(
            effects=[
                StaticColorEffect(Colors.RED, hold_seconds=0.0),
                OffEffect(),
                StaticColorEffect(Colors.GREEN, hold_seconds=0.0),
            ],
            repeat=1,
        ).run(ctx)
        assert b.method_names() == ["single_color", "off", "single_color"]
        assert b.calls[0].args == (Colors.RED,)
        assert b.calls[2].args == (Colors.GREEN,)

    def test_repeat(self):
        b = RecordingBackend()
        ctx = make_ctx(b)
        SequenceEffect(
            effects=[OffEffect()],
            repeat=3,
        ).run(ctx)
        assert b.method_names() == ["off", "off", "off"]


# ============================================================
# EffectRegistry
# ============================================================


class TestEffectRegistry:
    def test_register_and_get(self):
        reg = EffectRegistry()
        eff = OffEffect()
        reg.register("my_off", eff)
        assert reg.get("my_off") is eff

    def test_unknown_raises(self):
        reg = EffectRegistry()
        with pytest.raises(KeyError, match="Unknown effect"):
            reg.get("nope")

    def test_has(self):
        reg = EffectRegistry({"a": OffEffect()})
        assert reg.has("a")
        assert not reg.has("b")

    def test_contains(self):
        reg = EffectRegistry({"a": OffEffect()})
        assert "a" in reg

    def test_len(self):
        reg = EffectRegistry({"a": OffEffect(), "b": OffEffect()})
        assert len(reg) == 2

    def test_list_names(self):
        reg = EffectRegistry({"b": OffEffect(), "a": OffEffect()})
        assert reg.list_names() == ["a", "b"]

    def test_list_by_group(self):
        reg = EffectRegistry({
            "state_idle": OffEffect(),
            "state_active": OffEffect(),
            "event_error": OffEffect(),
        })
        assert reg.list_by_group("state_") == ["state_active", "state_idle"]

    def test_merge(self):
        a = EffectRegistry({"x": OffEffect()})
        b = EffectRegistry({"y": OffEffect()})
        a.merge(b)
        assert "x" in a and "y" in a

    def test_merge_no_overwrite(self):
        original = OffEffect(hold_seconds=1.0)
        a = EffectRegistry({"x": original})
        b = EffectRegistry({"x": OffEffect(hold_seconds=2.0)})
        a.merge(b, overwrite=False)
        assert a.get("x") is original

    def test_merge_overwrite(self):
        a = EffectRegistry({"x": OffEffect(hold_seconds=1.0)})
        replacement = OffEffect(hold_seconds=2.0)
        b = EffectRegistry({"x": replacement})
        a.merge(b, overwrite=True)
        assert a.get("x") is replacement

    def test_copy(self):
        a = EffectRegistry({"x": OffEffect()})
        b = a.copy()
        b.register("y", OffEffect())
        assert "y" not in a

    def test_unregister(self):
        reg = EffectRegistry({"a": OffEffect()})
        reg.unregister("a")
        assert not reg.has("a")

    def test_iter(self):
        reg = EffectRegistry({"b": OffEffect(), "a": OffEffect()})
        assert list(reg) == ["a", "b"]


# ============================================================
# Config Loader
# ============================================================


class TestParseEffectSpec:
    def test_off(self):
        e = parse_effect_spec({"type": "off", "hold_seconds": 0.5})
        assert isinstance(e, OffEffect)
        assert e.hold_seconds == 0.5

    def test_static(self):
        e = parse_effect_spec({"type": "static", "color": "red"})
        assert isinstance(e, StaticColorEffect)
        assert e.color == Colors.RED

    def test_static_with_hex_color(self):
        e = parse_effect_spec({"type": "static", "color": "#00FF00"})
        assert isinstance(e, StaticColorEffect)
        assert e.color == RGB(0, 255, 0)

    def test_static_with_tuple_color(self):
        e = parse_effect_spec({"type": "static", "color": [128, 64, 32]})
        assert isinstance(e, StaticColorEffect)
        assert e.color == RGB(128, 64, 32)

    def test_breath(self):
        e = parse_effect_spec({
            "type": "breath",
            "color": "cyan",
            "speed": 3,
            "brightness": 200,
            "persistent": True,
        })
        assert isinstance(e, BreathEffect)
        assert e.speed == 3
        assert e.persistent is True

    def test_rainbow(self):
        e = parse_effect_spec({"type": "rainbow", "speed": 5})
        assert isinstance(e, RainbowEffect)
        assert e.speed == 5

    def test_blink(self):
        e = parse_effect_spec({
            "type": "blink",
            "color": "yellow",
            "on_seconds": 0.2,
            "off_seconds": 0.1,
            "repeat": 4,
        })
        assert isinstance(e, BlinkEffect)
        assert e.repeat == 4

    def test_blink_no_repeat(self):
        e = parse_effect_spec({"type": "blink", "color": "red"})
        assert isinstance(e, BlinkEffect)
        assert e.repeat is None

    def test_alternate(self):
        e = parse_effect_spec({
            "type": "alternate",
            "colors": ["red", "green", "#0000FF"],
            "interval_seconds": 0.5,
            "repeat": 2,
        })
        assert isinstance(e, AlternateColorEffect)
        assert len(e.colors) == 3
        assert e.colors[2] == RGB(0, 0, 255)

    def test_doa(self):
        e = parse_effect_spec({
            "type": "doa",
            "base_color": "soft_blue",
            "doa_color": "yellow",
        })
        assert isinstance(e, DoaEffect)

    def test_fade(self):
        e = parse_effect_spec({
            "type": "fade",
            "from_color": "black",
            "to_color": "white",
            "duration": 2.0,
            "steps": 10,
        })
        assert isinstance(e, FadeEffect)
        assert e.steps == 10

    def test_sequence(self):
        e = parse_effect_spec({
            "type": "sequence",
            "effects": [
                {"type": "static", "color": "red", "hold_seconds": 0.1},
                {"type": "off"},
            ],
            "repeat": 2,
        })
        assert isinstance(e, SequenceEffect)
        assert len(e.effects) == 2
        assert e.repeat == 2

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown effect type"):
            parse_effect_spec({"type": "nonexistent"})


class TestLoadEffectsFromDict:
    def test_multiple_effects(self):
        data = {
            "my_idle": {"type": "breath", "color": "green", "persistent": True},
            "my_error": {"type": "blink", "color": "red", "repeat": 3},
        }
        effects = load_effects_from_dict(data)
        assert "my_idle" in effects
        assert "my_error" in effects
        assert isinstance(effects["my_idle"], BreathEffect)


class TestLoadEffectsFromJson:
    def test_from_file(self, tmp_path: Path):
        data = {
            "test_off": {"type": "off", "hold_seconds": 1.0},
            "test_blink": {"type": "blink", "color": [255, 0, 0], "repeat": 1},
        }
        fp = tmp_path / "effects.json"
        fp.write_text(json.dumps(data), encoding="utf-8")
        effects = load_effects_from_json(fp)
        assert "test_off" in effects
        assert isinstance(effects["test_blink"], BlinkEffect)

    def test_from_string(self):
        data = {"x": {"type": "off"}}
        effects = load_effects_from_json(json.dumps(data))
        assert "x" in effects


# ============================================================
# Standard Library
# ============================================================


class TestStandardLibrary:
    def test_builds_without_error(self):
        effects = build_standard_effects()
        assert len(effects) > 0

    def test_contains_expected_groups(self):
        effects = build_standard_effects()
        names = list(effects.keys())
        assert any(n.startswith("state_") for n in names)
        assert any(n.startswith("event_") for n in names)
        assert any(n.startswith("system_") for n in names)

    def test_expected_state_effects(self):
        effects = build_standard_effects()
        for name in [
            "state_idle",
            "state_waiting",
            "state_processing",
            "state_listening",
            "state_thinking",
            "state_speaking",
            "state_muted",
            "state_offline",
            "state_connecting",
            "state_doa",
        ]:
            assert name in effects, f"Missing: {name}"

    def test_expected_event_effects(self):
        effects = build_standard_effects()
        for name in [
            "event_success",
            "event_warning",
            "event_error",
            "event_notification",
            "event_connected",
            "event_disconnected",
            "event_ack",
        ]:
            assert name in effects, f"Missing: {name}"

    def test_expected_system_effects(self):
        effects = build_standard_effects()
        assert "system_boot" in effects
        assert "system_shutdown" in effects

    def test_all_are_led_effect_instances(self):
        for name, effect in build_standard_effects().items():
            assert isinstance(effect, LedEffect), f"{name} is not LedEffect"

    def test_build_standard_registry(self):
        reg = build_standard_registry()
        assert isinstance(reg, EffectRegistry)
        assert len(reg) > 0


# ============================================================
# Controller
# ============================================================


class TestController:
    def test_create_with_defaults(self):
        b = RecordingBackend()
        ctrl = LedRingController(b)
        assert len(ctrl.list_effects()) > 0

    def test_create_with_custom_dict(self):
        b = RecordingBackend()
        ctrl = LedRingController(b, effects={"my_off": OffEffect()})
        assert ctrl.list_effects() == ["my_off"]

    def test_create_with_registry(self):
        b = RecordingBackend()
        reg = EffectRegistry({"my_off": OffEffect()})
        ctrl = LedRingController(b, effects=reg)
        assert ctrl.list_effects() == ["my_off"]

    def test_register_effect(self):
        b = RecordingBackend()
        ctrl = LedRingController(b, effects={})
        ctrl.register_effect("x", OffEffect())
        assert "x" in ctrl.list_effects()

    def test_set_state_unknown_raises(self):
        b = RecordingBackend()
        ctrl = LedRingController(b, effects={})
        with pytest.raises(KeyError):
            ctrl.set_state("nonexistent")

    def test_set_state_runs_effect(self):
        b = RecordingBackend()
        ctrl = LedRingController(
            b,
            effects={"s1": StaticColorEffect(Colors.RED, persistent=True)},
        )
        ctrl.set_state("s1")
        time.sleep(0.1)
        assert any(c.method == "single_color" for c in b.calls)
        assert ctrl.current_state == "s1"
        ctrl.stop_all()

    def test_clear_state(self):
        b = RecordingBackend()
        ctrl = LedRingController(
            b,
            effects={"s1": StaticColorEffect(Colors.RED, persistent=True)},
        )
        ctrl.set_state("s1")
        time.sleep(0.05)
        ctrl.clear_state(turn_off=True)
        assert ctrl.current_state is None
        assert "off" in b.method_names()

    def test_play_event_runs_effect(self):
        b = RecordingBackend()
        ctrl = LedRingController(
            b,
            effects={"e1": BlinkEffect(Colors.GREEN, on_seconds=0.01, off_seconds=0.01, repeat=1)},
        )
        ctrl.play_event("e1")
        assert "single_color" in b.method_names()

    def test_play_event_restores_state(self):
        b = RecordingBackend()
        ctrl = LedRingController(
            b,
            effects={
                "s1": StaticColorEffect(Colors.RED, persistent=True),
                "e1": BlinkEffect(Colors.GREEN, on_seconds=0.01, off_seconds=0.01, repeat=1),
            },
        )
        ctrl.set_state("s1")
        time.sleep(0.05)
        ctrl.play_event("e1")
        time.sleep(0.1)
        assert ctrl.current_state == "s1"
        ctrl.stop_all()

    def test_stop_all(self):
        b = RecordingBackend()
        ctrl = LedRingController(
            b,
            effects={"s1": StaticColorEffect(Colors.RED, persistent=True)},
        )
        ctrl.set_state("s1")
        time.sleep(0.05)
        ctrl.stop_all()
        assert ctrl.current_state is None

    def test_show_progress(self):
        b = RecordingBackend()
        ctrl = LedRingController(b, effects={})
        ctrl.show_progress(0.5)
        assert "single_color" in b.method_names()

    def test_pulse_color(self):
        b = RecordingBackend()
        ctrl = LedRingController(b, effects={})
        ctrl.pulse_color(Colors.CYAN, pulses=2, on_seconds=0.01, off_seconds=0.01)
        assert b.method_names().count("single_color") == 2

    def test_progress_color_range(self):
        red = LedRingController._progress_color(0.0)
        assert red == Colors.RED
        yellow = LedRingController._progress_color(0.5)
        assert yellow == Colors.YELLOW
        green = LedRingController._progress_color(1.0)
        assert green == Colors.GREEN


# ============================================================
# Integration: config → registry → controller
# ============================================================


class TestIntegration:
    def test_config_dict_to_controller(self):
        spec = {
            "my_idle": {
                "type": "breath",
                "color": "soft_green",
                "speed": 1,
                "brightness": 60,
                "persistent": True,
            },
            "my_alert": {
                "type": "blink",
                "color": [255, 0, 0],
                "on_seconds": 0.01,
                "off_seconds": 0.01,
                "repeat": 2,
            },
        }
        effects = load_effects_from_dict(spec)
        reg = EffectRegistry(effects)
        b = RecordingBackend()
        ctrl = LedRingController(b, effects=reg)

        ctrl.set_state("my_idle")
        time.sleep(0.1)
        assert any(c.method == "breath" for c in b.calls)

        b.clear()
        ctrl.play_event("my_alert")
        assert "single_color" in b.method_names()

        ctrl.stop_all()

    def test_json_file_to_controller(self, tmp_path: Path):
        data = {
            "led_on": {"type": "static", "color": "#00FF00"},
            "led_off": {"type": "off"},
        }
        fp = tmp_path / "effects.json"
        fp.write_text(json.dumps(data), encoding="utf-8")

        effects = load_effects_from_json(fp)
        b = RecordingBackend()
        ctrl = LedRingController(b, effects=effects)
        ctrl.play_event("led_on")
        assert b.calls[0].args == (RGB(0, 255, 0),)

    def test_merge_stdlib_with_custom(self):
        stdlib = build_standard_registry()
        custom = EffectRegistry(load_effects_from_dict({
            "my_special": {"type": "static", "color": "pink"},
        }))
        stdlib.merge(custom)
        assert "state_idle" in stdlib
        assert "my_special" in stdlib
