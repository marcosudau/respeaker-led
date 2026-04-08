"""Thread-safe LED ring controller with state / event separation."""
from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from .backend import LedRingBackend
from .context import EffectContext
from .effects import BlinkEffect, LedEffect, StaticColorEffect
from .registry import EffectRegistry
from .rgb import RGB, Colors
from .stdlib import build_standard_effects


class LedRingController:
    """High-level controller that manages states (looping) and events (one-shot).

    *States* are long-running effects (idle glow, listening breath, …).
    Only one state can be active at a time; it runs in a background thread
    and loops until replaced or cleared.

    *Events* are short one-shot effects (success blink, error flash, …).
    They interrupt the current state, play once, and then the state resumes.
    """

    def __init__(
        self,
        backend: LedRingBackend,
        effects: EffectRegistry | dict[str, LedEffect] | None = None,
        logger: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.backend = backend
        self.logger = logger

        if effects is None:
            self.effects = EffectRegistry(build_standard_effects())
        elif isinstance(effects, dict):
            self.effects = EffectRegistry(effects)
        else:
            self.effects = effects

        self._state_lock = threading.RLock()
        self._playback_lock = threading.Lock()
        self._event_active = threading.Event()

        self._desired_state_name: str | None = None
        self._state_thread: threading.Thread | None = None
        self._state_stop_event: threading.Event | None = None

    # -- Logging ------------------------------------------------------

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger(message)

    # -- Effect access ------------------------------------------------

    def register_effect(self, name: str, effect: LedEffect) -> None:
        self.effects.register(name, effect)

    def list_effects(self) -> list[str]:
        return self.effects.list_names()

    def get_effect(self, name: str) -> LedEffect:
        return self.effects.get(name)

    # -- Internal thread helpers --------------------------------------

    def _run_state_effect(
        self, effect: LedEffect, stop_event: threading.Event
    ) -> None:
        ctx = EffectContext(backend=self.backend, stop_event=stop_event)
        try:
            effect.run(ctx)
        except Exception as exc:
            self._log(f"[STATE ERROR] {exc}")

    def _stop_state_thread_locked(self, turn_off: bool = False) -> None:
        thread = self._state_thread
        stop_event = self._state_stop_event

        self._state_thread = None
        self._state_stop_event = None

        if stop_event:
            stop_event.set()

        if thread and thread.is_alive():
            thread.join(timeout=2.0)

        if turn_off:
            try:
                self.backend.off()
            except Exception as exc:
                self._log(f"[OFF ERROR] {exc}")

    def _restart_state_locked(self) -> None:
        self._stop_state_thread_locked(turn_off=False)

        if self._desired_state_name is None:
            return

        if self._event_active.is_set():
            return

        effect = self.get_effect(self._desired_state_name)
        stop_event = threading.Event()
        thread = threading.Thread(
            target=self._run_state_effect,
            args=(effect, stop_event),
            daemon=True,
        )

        self._state_stop_event = stop_event
        self._state_thread = thread
        thread.start()

    # -- Public: state management -------------------------------------

    def set_state(self, name: str) -> None:
        """Set the active background state effect (replaces the previous one)."""
        _ = self.get_effect(name)
        with self._state_lock:
            self._desired_state_name = name
            self._restart_state_locked()

    @property
    def current_state(self) -> str | None:
        return self._desired_state_name

    def clear_state(self, turn_off: bool = True) -> None:
        with self._state_lock:
            self._desired_state_name = None
            self._stop_state_thread_locked(turn_off=turn_off)

    def stop_all(self, turn_off: bool = True) -> None:
        self.clear_state(turn_off=turn_off)

    # -- Public: event playback ---------------------------------------

    def _run_one_shot_effect(self, effect: LedEffect) -> None:
        ctx = EffectContext(backend=self.backend, stop_event=threading.Event())
        effect.run(ctx)

    def play_event(
        self,
        name: str,
        restore_state: bool = True,
        asynchronous: bool = False,
    ) -> None:
        """Play a one-shot event effect.

        If *restore_state* is ``True`` the previous state resumes afterwards.
        """
        effect = self.get_effect(name)

        def _worker() -> None:
            with self._playback_lock:
                self._event_active.set()
                try:
                    with self._state_lock:
                        previous_state = self._desired_state_name
                        self._stop_state_thread_locked(turn_off=False)

                    self._run_one_shot_effect(effect)

                finally:
                    self._event_active.clear()
                    if restore_state:
                        with self._state_lock:
                            if (
                                previous_state is not None
                                and self._desired_state_name == previous_state
                            ):
                                self._restart_state_locked()

        if asynchronous:
            threading.Thread(target=_worker, daemon=True).start()
        else:
            _worker()

    # -- Public: dynamic helpers --------------------------------------

    @staticmethod
    def _progress_color(progress: float) -> RGB:
        progress = max(0.0, min(1.0, progress))
        if progress <= 0.5:
            local = progress / 0.5
            return Colors.RED.blend(Colors.YELLOW, local)
        local = (progress - 0.5) / 0.5
        return Colors.YELLOW.blend(Colors.GREEN, local)

    def show_progress(
        self,
        progress: float,
        hold_seconds: float = 0.0,
        restore_state: bool = True,
    ) -> None:
        """Display a progress colour (red → yellow → green)."""
        progress = max(0.0, min(1.0, progress))
        color = self._progress_color(progress)
        effect = StaticColorEffect(
            color=color, hold_seconds=hold_seconds, persistent=False
        )

        with self._playback_lock:
            self._event_active.set()
            try:
                with self._state_lock:
                    previous_state = self._desired_state_name
                    self._stop_state_thread_locked(turn_off=False)

                self._run_one_shot_effect(effect)

            finally:
                self._event_active.clear()
                if restore_state:
                    with self._state_lock:
                        if (
                            previous_state is not None
                            and self._desired_state_name == previous_state
                        ):
                            self._restart_state_locked()

    def run_countdown(
        self,
        total_seconds: int,
        restore_state: bool = True,
        final_event: str = "event_error",
    ) -> None:
        """Show a countdown from *total_seconds* to zero, then play *final_event*."""
        total_seconds = max(1, int(total_seconds))

        with self._playback_lock:
            self._event_active.set()
            try:
                with self._state_lock:
                    previous_state = self._desired_state_name
                    self._stop_state_thread_locked(turn_off=False)

                for remaining in range(total_seconds, 0, -1):
                    ratio = remaining / total_seconds
                    color = self._progress_color(ratio)

                    if remaining > 3:
                        self.backend.single_color(color)
                        time.sleep(1.0)
                    else:
                        for _ in range(2):
                            self.backend.single_color(color)
                            time.sleep(0.20)
                            self.backend.off()
                            time.sleep(0.15)
                        time.sleep(0.30)

                if self.effects.has(final_event):
                    self._run_one_shot_effect(self.get_effect(final_event))

            finally:
                self._event_active.clear()
                if restore_state:
                    with self._state_lock:
                        if (
                            previous_state is not None
                            and self._desired_state_name == previous_state
                        ):
                            self._restart_state_locked()

    def pulse_color(
        self,
        color: RGB,
        pulses: int = 2,
        on_seconds: float = 0.12,
        off_seconds: float = 0.08,
        restore_state: bool = True,
    ) -> None:
        """Quick helper: blink a colour N times."""
        effect = BlinkEffect(
            color=color,
            on_seconds=on_seconds,
            off_seconds=off_seconds,
            repeat=max(1, pulses),
        )

        with self._playback_lock:
            self._event_active.set()
            try:
                with self._state_lock:
                    previous_state = self._desired_state_name
                    self._stop_state_thread_locked(turn_off=False)

                self._run_one_shot_effect(effect)

            finally:
                self._event_active.clear()
                if restore_state:
                    with self._state_lock:
                        if (
                            previous_state is not None
                            and self._desired_state_name == previous_state
                        ):
                            self._restart_state_locked()
