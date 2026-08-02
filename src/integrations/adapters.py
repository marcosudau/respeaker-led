from __future__ import annotations

import importlib.util
import math
import threading
from typing import Protocol, runtime_checkable

from ..core.models import Frame
from ..infrastructure.logging_utils import get_logger
from ..infrastructure.paths import XVF_HOST_PATH


logger = get_logger(__name__)


class FrameAdapter(Protocol):
    def apply_frame(self, frame: Frame) -> None: ...
    def close(self) -> None: ...


@runtime_checkable
class DoAInputAdapter(Protocol):
    def read_doa_inputs(self) -> dict[str, object]: ...


class ConsolePreviewAdapter:
    def __init__(
        self,
        *,
        show_timestamp: bool = True,
        emit_output: bool = True,
        emit_only_on_change: bool = False,
    ) -> None:
        self.last_frame: Frame | None = None
        self.show_timestamp = show_timestamp
        self.emit_output = emit_output
        self.emit_only_on_change = emit_only_on_change

    def apply_frame(self, frame: Frame) -> None:
        previous = self.last_frame
        self.last_frame = frame
        if not self.emit_output:
            return
        if self.emit_only_on_change and previous is not None and previous.leds == frame.leds:
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
        self._last_leds: tuple[int, ...] | None = None
        self._io_lock = threading.RLock()

    def apply_frame(self, frame: Frame) -> None:
        leds = tuple(frame.leds)
        with self._io_lock:
            if not self._ring_mode:
                self._device.write("LED_EFFECT", [5])
                self._ring_mode = True
            if leds == self._last_leds:
                return
            self._device.write("LED_RING_COLOR", list(leds))
            self._last_leds = leds

    def read_doa_inputs(self) -> dict[str, object]:
        with self._io_lock:
            payload = self._device.read("DOA_VALUE")
        if not isinstance(payload, tuple) or len(payload) != 2:
            logger.warning("DOA DEBUG invalid payload=%r", payload)
            raise RuntimeError(f"Unexpected DOA_VALUE payload: {payload!r}")

        direction_raw = payload[0]
        if isinstance(direction_raw, bool) or not isinstance(direction_raw, (int, float)):
            logger.warning("DOA DEBUG invalid direction payload=%r", payload)
            raise RuntimeError(f"Invalid DOA_VALUE direction: {direction_raw!r}")
        direction = float(direction_raw)
        if not math.isfinite(direction) or not 0.0 <= direction < 360.0:
            logger.warning("DOA DEBUG direction out of range payload=%r", payload)
            raise RuntimeError(f"DOA_VALUE direction is out of range: {direction_raw!r}")

        vad_raw = payload[1]
        if isinstance(vad_raw, bool):
            vad_active = vad_raw
        elif isinstance(vad_raw, int) and vad_raw in {0, 1}:
            vad_active = bool(vad_raw)
        else:
            logger.warning("DOA DEBUG invalid VAD flag payload=%r", payload)
            raise RuntimeError(f"Invalid DOA_VALUE VAD flag: {vad_raw!r}")
        logger.debug(
            "DOA sample payload=%r direction_deg=%.1f vad_active=%s",
            payload,
            direction,
            vad_active,
        )
        return {
            "direction_deg": direction,
            "detection_state": "sound" if vad_active else "none",
        }

    def close(self) -> None:
        with self._io_lock:
            self._device.close()
