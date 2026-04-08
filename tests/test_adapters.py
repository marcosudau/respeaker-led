from __future__ import annotations

from types import SimpleNamespace

from src.adapters import ConsolePreviewAdapter, MemoryFrameAdapter, ReSpeakerAdapter
from src.models import Frame, LED_COUNT
from src.paths import XVF_HOST_PATH


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
    adapter.close()

    assert recorded["name"] == "xvf_host_module"
    assert recorded["path"] == XVF_HOST_PATH
    assert writes == [
        ("LED_EFFECT", [5]),
        ("LED_RING_COLOR", frame.leds),
        ("close", None),
    ]
