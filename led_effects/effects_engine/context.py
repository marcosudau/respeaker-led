"""Effect execution context with cooperative cancellation."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from .backend import LedRingBackend


@dataclass
class EffectContext:
    """Passed to every effect's ``run()`` method.

    Provides the backend to control LEDs and a cooperative stop mechanism
    so the controller can interrupt long-running or looping effects.
    """

    backend: LedRingBackend
    stop_event: threading.Event

    @property
    def is_stopped(self) -> bool:
        return self.stop_event.is_set()

    def sleep(self, seconds: float, chunk: float = 0.05) -> bool:
        """Sleep for *seconds* while checking the stop event.

        Returns ``True`` if the full duration elapsed (not stopped).
        """
        end_time = time.monotonic() + max(0.0, seconds)
        while time.monotonic() < end_time:
            if self.stop_event.is_set():
                return False
            remaining = end_time - time.monotonic()
            time.sleep(min(chunk, max(0.001, remaining)))
        return not self.stop_event.is_set()

    def wait_until_stopped(self, chunk: float = 0.1) -> None:
        """Block until the stop event is set (for persistent effects)."""
        while not self.stop_event.is_set():
            time.sleep(chunk)
