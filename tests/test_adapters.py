from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.integrations.adapters import ConsolePreviewAdapter, MemoryFrameAdapter, ReSpeakerAdapter
from src.core.models import Frame, LED_COUNT
from src.infrastructure.paths import XVF_HOST_PATH


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


def test_respeaker_adapter_loads_driver_from_expected_path(monkeypatch):
    recorded: dict[str, object] = {}
    writes: list[tuple[str, object]] = []

    class FakeDevice:
        def write(self, command: str, payload):
            writes.append((command, payload))

        def close(self) -> None:
            writes.append(("close", None))

    class FakeLoader:
        def exec_module(self, module) -> None:
            module.find = lambda: FakeDevice()

    def fake_spec_from_file_location(name: str, path):
        recorded["name"] = name
        recorded["path"] = path
        return SimpleNamespace(loader=FakeLoader())

    monkeypatch.setattr("importlib.util.spec_from_file_location", fake_spec_from_file_location)
    monkeypatch.setattr("importlib.util.module_from_spec", lambda spec: SimpleNamespace())

    adapter = ReSpeakerAdapter()
    frame = Frame(leds=list(range(LED_COUNT)), timestamp=0.0)
    adapter.apply_frame(frame)
    adapter.apply_frame(frame)
    adapter.close()

    assert recorded["name"] == "xvf_host_module"
    assert recorded["path"] == XVF_HOST_PATH
    assert writes == [
        ("LED_EFFECT", [5]),
        ("LED_RING_COLOR", frame.leds),
        ("close", None),
    ]


def test_respeaker_adapter_reads_doa_value_without_led_side_effects(monkeypatch, caplog):
    reads: list[str] = []
    writes: list[tuple[str, object]] = []

    class FakeDevice:
        def read(self, command: str):
            reads.append(command)
            return (135, 1)

        def write(self, command: str, payload):
            writes.append((command, payload))

        def close(self) -> None:
            return None

    class FakeLoader:
        def exec_module(self, module) -> None:
            module.find = lambda: FakeDevice()

    monkeypatch.setattr(
        "importlib.util.spec_from_file_location",
        lambda name, path: SimpleNamespace(loader=FakeLoader()),
    )
    monkeypatch.setattr("importlib.util.module_from_spec", lambda spec: SimpleNamespace())

    with caplog.at_level("DEBUG", logger="led_controller.integrations.adapters"):
        inputs = ReSpeakerAdapter().read_doa_inputs()

    assert reads == ["DOA_VALUE"]
    assert inputs == {"direction_deg": 135.0, "detection_state": "sound"}
    assert writes == []
    assert (
        "DOA sample payload=(135, 1) direction_deg=135.0 vad_active=True"
    ) in caplog.messages


def test_respeaker_adapter_maps_inactive_vad_flag_to_none(monkeypatch):
    class FakeDevice:
        def read(self, command: str):
            assert command == "DOA_VALUE"
            return (275, 0)

        def close(self) -> None:
            return None

    class FakeLoader:
        def exec_module(self, module) -> None:
            module.find = lambda: FakeDevice()

    monkeypatch.setattr(
        "importlib.util.spec_from_file_location",
        lambda name, path: SimpleNamespace(loader=FakeLoader()),
    )
    monkeypatch.setattr("importlib.util.module_from_spec", lambda spec: SimpleNamespace())

    assert ReSpeakerAdapter().read_doa_inputs() == {
        "direction_deg": 275.0,
        "detection_state": "none",
    }


def test_respeaker_adapter_rejects_invalid_doa_value(monkeypatch):
    class FakeDevice:
        def read(self, command: str):
            return (999, 1)

        def close(self) -> None:
            return None

    class FakeLoader:
        def exec_module(self, module) -> None:
            module.find = lambda: FakeDevice()

    monkeypatch.setattr(
        "importlib.util.spec_from_file_location",
        lambda name, path: SimpleNamespace(loader=FakeLoader()),
    )
    monkeypatch.setattr("importlib.util.module_from_spec", lambda spec: SimpleNamespace())

    with pytest.raises(RuntimeError, match="out of range"):
        ReSpeakerAdapter().read_doa_inputs()


def test_respeaker_adapter_rejects_invalid_vad_flag(monkeypatch):
    class FakeDevice:
        def read(self, command: str):
            return (180, 7)

        def close(self) -> None:
            return None

    class FakeLoader:
        def exec_module(self, module) -> None:
            module.find = lambda: FakeDevice()

    monkeypatch.setattr(
        "importlib.util.spec_from_file_location",
        lambda name, path: SimpleNamespace(loader=FakeLoader()),
    )
    monkeypatch.setattr("importlib.util.module_from_spec", lambda spec: SimpleNamespace())

    with pytest.raises(RuntimeError, match="VAD flag"):
        ReSpeakerAdapter().read_doa_inputs()
