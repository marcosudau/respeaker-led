from __future__ import annotations

import time

from led_effects.effects_engine import Colors, EasyLedRing, RecordingBackend, easy_hardware, easy_preview


def _wait_for_calls(backend: RecordingBackend, minimum: int = 1, timeout: float = 0.5) -> None:
    deadline = time.monotonic() + timeout
    while len(backend.calls) < minimum and time.monotonic() < deadline:
        time.sleep(0.01)


def test_show_resolves_state_alias():
    backend = RecordingBackend()
    ring = EasyLedRing(backend)

    ring.show("idle")
    _wait_for_calls(backend)

    assert ring.controller.current_state == "state_idle"
    assert any(call.method == "breath" for call in backend.calls)
    ring.off()


def test_show_resolves_event_alias():
    backend = RecordingBackend()
    ring = EasyLedRing(backend)

    ring.show("success")

    methods = [call.method for call in backend.calls]
    assert "single_color" in methods
    assert "off" in methods


def test_color_is_simple_state():
    backend = RecordingBackend()
    ring = EasyLedRing(backend)

    ring.color("blue")
    _wait_for_calls(backend)

    assert backend.calls[0].method == "single_color"
    assert backend.calls[0].args[0] == Colors.BLUE
    ring.off()


def test_blink_runs_one_shot_event():
    backend = RecordingBackend()
    ring = EasyLedRing(backend)

    ring.blink("red", times=2)

    methods = [call.method for call in backend.calls]
    assert methods.count("single_color") == 2
    assert methods.count("off") == 2


def test_spinner_can_run_for_seconds_then_stop():
    backend = RecordingBackend()
    ring = EasyLedRing(backend)

    ring.spinner(seconds=0.08)

    assert any(call.method == "set_ring_colors" for call in backend.calls)
    assert backend.calls[-1].method == "off"


def test_timer_uses_advanced_ring_frames():
    backend = RecordingBackend()
    ring = EasyLedRing(backend)

    ring.timer(0.2)

    assert any(call.method == "set_ring_colors" for call in backend.calls)


def test_progress_shows_ring_frame_once():
    backend = RecordingBackend()
    ring = EasyLedRing(backend)

    ring.progress(0.5)

    ring_calls = [call for call in backend.calls if call.method == "set_ring_colors"]
    assert len(ring_calls) == 1
    assert len(ring_calls[0].args[0]) == 12


def test_pointer_shows_static_direction_frame():
    backend = RecordingBackend()
    ring = EasyLedRing(backend)

    ring.pointer(90)

    ring_call = next(call for call in backend.calls if call.method == "set_ring_colors")
    colors = ring_call.args[0]
    assert colors[3] == Colors.CYAN


def test_choices_are_easy_names_without_prefixes():
    ring = EasyLedRing(RecordingBackend())

    choices = ring.choices()

    assert "idle" in choices["states"]
    assert "success" in choices["events"]
    assert "boot" in choices["system"]


def test_easy_preview_uses_dry_run_backend():
    ring = easy_preview(logger=None)
    assert ring.backend.__class__.__name__ == "DryRunBackend"


def test_easy_hardware_uses_default_xvf_host_path():
    ring = easy_hardware(dry_run=True, logger=None)
    assert ring.backend.host_path.name == "xvf_host.py"