from __future__ import annotations

import pytest

from src.integrations.adapters import ConsolePreviewAdapter, MemoryFrameAdapter, ReSpeakerAdapter
from src.core.models import Frame, LED_COUNT


def test_console_preview_adapter_formats_frame(capsys):
    adapter = ConsolePreviewAdapter(show_timestamp=False)
    frame = Frame(leds=list(range(LED_COUNT)), timestamp=1.25)

    adapter.apply_frame(frame)

    expected = " ".join(f"{color:06X}" for color in range(LED_COUNT))
    assert capsys.readouterr().out.strip() == expected
    assert adapter.last_frame is frame


def test_memory_frame_adapter_keeps_last_frame_without_output(capsys):
    adapter = MemoryFrameAdapter()
    frame = Frame(leds=[0x112233] * LED_COUNT, timestamp=2.0)

    adapter.apply_frame(frame)

    assert capsys.readouterr().out == ""
    assert adapter.last_frame is frame


def test_respeaker_adapter_loads_driver_from_expected_path():
    writes: list[tuple[str, object]] = []
    closed = []

    class FakeUsbManager:
        @property
        def is_connected(self) -> bool:
            return True

        def consume_ring_mode_dirty(self) -> bool:
            return False

        def write(self, name: str, data: list) -> None:
            writes.append((name, data))

        def read(self, name: str):
            return ()

        def close(self) -> None:
            closed.append(True)

    manager = FakeUsbManager()
    adapter = ReSpeakerAdapter(usb_manager=manager)
    frame = Frame(leds=list(range(LED_COUNT)), timestamp=0.0)
    adapter.apply_frame(frame)
    adapter.apply_frame(frame)
    adapter.close()

    assert writes == [
        ("LED_EFFECT", [5]),
        ("LED_RING_COLOR", frame.leds),
    ]
    assert closed == [True]


def test_respeaker_adapter_reads_doa_value_without_led_side_effects(caplog):
    reads: list[str] = []
    writes: list[tuple[str, object]] = []

    class FakeUsbManager:
        @property
        def is_connected(self) -> bool:
            return True

        def consume_ring_mode_dirty(self) -> bool:
            return False

        def write(self, name: str, data: list) -> None:
            writes.append((name, data))

        def read(self, name: str):
            reads.append(name)
            return (135, 1)

        def close(self) -> None:
            return None

    with caplog.at_level("DEBUG", logger="led_controller.integrations.adapters"):
        inputs = ReSpeakerAdapter(usb_manager=FakeUsbManager()).read_doa_inputs()

    assert reads == ["DOA_VALUE"]
    assert inputs == {"direction_deg": 135.0, "detection_state": "sound"}
    assert writes == []
    assert (
        "DOA sample payload=(135, 1) direction_deg=135.0 vad_active=True"
    ) in caplog.messages


def test_respeaker_adapter_maps_inactive_vad_flag_to_none():
    class FakeUsbManager:
        @property
        def is_connected(self) -> bool:
            return True

        def consume_ring_mode_dirty(self) -> bool:
            return False

        def write(self, name: str, data: list) -> None:
            pass

        def read(self, name: str):
            assert name == "DOA_VALUE"
            return (275, 0)

        def close(self) -> None:
            return None

    assert ReSpeakerAdapter(usb_manager=FakeUsbManager()).read_doa_inputs() == {
        "direction_deg": 275.0,
        "detection_state": "none",
    }


def test_respeaker_adapter_rejects_invalid_doa_value():
    class FakeUsbManager:
        @property
        def is_connected(self) -> bool:
            return True

        def consume_ring_mode_dirty(self) -> bool:
            return False

        def write(self, name: str, data: list) -> None:
            pass

        def read(self, name: str):
            return (999, 1)

        def close(self) -> None:
            return None

    with pytest.raises(RuntimeError, match="out of range"):
        ReSpeakerAdapter(usb_manager=FakeUsbManager()).read_doa_inputs()


def test_respeaker_adapter_rejects_invalid_vad_flag():
    class FakeUsbManager:
        @property
        def is_connected(self) -> bool:
            return True

        def consume_ring_mode_dirty(self) -> bool:
            return False

        def write(self, name: str, data: list) -> None:
            pass

        def read(self, name: str):
            return (180, 7)

        def close(self) -> None:
            return None

    with pytest.raises(RuntimeError, match="VAD flag"):
        ReSpeakerAdapter(usb_manager=FakeUsbManager()).read_doa_inputs()

