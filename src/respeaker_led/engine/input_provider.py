from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from ..core.effect_schema import InputContext


class PolledInputProvider:
    def __init__(
        self,
        provider_id: str,
        reader: Callable[[], dict[str, object] | None],
        *,
        max_hz: float,
    ) -> None:
        normalized_id = str(provider_id).strip()
        if not normalized_id:
            raise ValueError("provider_id must not be empty")
        if max_hz <= 0:
            raise ValueError("max_hz must be greater than zero")

        self.provider_id = normalized_id
        self.reader = reader
        self.max_hz = float(max_hz)
        self.interval_s = 1.0 / self.max_hz
        self._lock = threading.RLock()
        self._snapshot: dict[str, object] | None = None
        self._last_attempt_at: float | None = None
        self._last_success_at: float | None = None
        self._last_error: str | None = None
        self._poll_count = 0

    @property
    def last_error(self) -> str | None:
        with self._lock:
            return self._last_error

    def refresh(self, now: float) -> bool:
        with self._lock:
            if (
                self._last_attempt_at is not None
                and now - self._last_attempt_at < self.interval_s
            ):
                return False
            self._last_attempt_at = now
            self._poll_count += 1

        try:
            sampled = self.reader()
            if sampled is None:
                raise RuntimeError("input source returned no value")
            snapshot = dict(sampled)
        except Exception as exc:
            with self._lock:
                self._last_error = str(exc)
            return True

        with self._lock:
            self._snapshot = snapshot
            self._last_success_at = now
            self._last_error = None
        return True

    def sample(self, _context: InputContext) -> dict[str, object] | None:
        with self._lock:
            if self._last_error is not None:
                raise RuntimeError(self._last_error)
            return None if self._snapshot is None else dict(self._snapshot)

    def status(self, now: float) -> dict[str, Any]:
        with self._lock:
            age_ms = (
                None
                if self._last_success_at is None
                else max(0, int(round((now - self._last_success_at) * 1000.0)))
            )
            return {
                "provider_id": self.provider_id,
                "max_hz": self.max_hz,
                "poll_count": self._poll_count,
                "last_attempt_at": self._last_attempt_at,
                "last_success_at": self._last_success_at,
                "age_ms": age_ms,
                "last_error": self._last_error,
                "available": self._snapshot is not None and self._last_error is None,
            }
