from __future__ import annotations

import importlib.util
from typing import Protocol

from .models import Frame
from .paths import XVF_HOST_PATH


class FrameAdapter(Protocol):
    def apply_frame(self, frame: Frame) -> None: ...
    def close(self) -> None: ...


class ConsolePreviewAdapter:
    def __init__(self, *, show_timestamp: bool = True, emit_output: bool = True) -> None:
        self.last_frame: Frame | None = None
        self.show_timestamp = show_timestamp
        self.emit_output = emit_output

    def apply_frame(self, frame: Frame) -> None:
        self.last_frame = frame
        if not self.emit_output:
            return
        encoded = " ".join(f"{color:06X}" for color in frame.leds)
        if self.show_timestamp:
            print(f"[preview {frame.timestamp:0.2f}] {encoded}")
        else:
            print(encoded)

    def close(self) -> None:
        return None


class MemoryFrameAdapter(ConsolePreviewAdapter):
    def __init__(self) -> None:
        super().__init__(show_timestamp=False, emit_output=False)


class ReSpeakerAdapter:
    def __init__(self) -> None:
        spec = importlib.util.spec_from_file_location("xvf_host_module", XVF_HOST_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load xvf_host.py from {XVF_HOST_PATH}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._module = module
        self._device = module.find()
        if not self._device:
            raise RuntimeError("No reSpeaker device found.")
        self._ring_mode = False

    def apply_frame(self, frame: Frame) -> None:
        if not self._ring_mode:
            self._device.write("LED_EFFECT", [5])
            self._ring_mode = True
        self._device.write("LED_RING_COLOR", frame.leds)

    def close(self) -> None:
        self._device.close()
