"""LED ring backend abstractions."""
from __future__ import annotations

import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .rgb import RGB


# ============================================================
# Exceptions
# ============================================================

class LedRingError(Exception):
    pass


class HostCommandError(LedRingError):
    pass


# ============================================================
# Abstract backend
# ============================================================

LED_COUNT = 12


class LedRingBackend(ABC):
    @abstractmethod
    def off(self) -> None: ...

    @abstractmethod
    def single_color(self, color: RGB) -> None: ...

    @abstractmethod
    def set_ring_colors(self, colors: list[RGB]) -> None:
        """Set each LED individually. *colors* must have exactly LED_COUNT entries."""
        ...

    @abstractmethod
    def breath(self, color: RGB, speed: int = 1, brightness: int = 128) -> None: ...

    @abstractmethod
    def rainbow(self, speed: int = 1, brightness: int = 128) -> None: ...

    @abstractmethod
    def doa(self, base_color: RGB, doa_color: RGB) -> None: ...

    @abstractmethod
    def power_led_ring(self, enabled: bool) -> None: ...


# ============================================================
# Recording backend (for testing)
# ============================================================

@dataclass
class RecordedCall:
    method: str
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)


class RecordingBackend(LedRingBackend):
    """Records every call for assertions in tests."""

    def __init__(self) -> None:
        self.calls: list[RecordedCall] = []

    def off(self) -> None:
        self.calls.append(RecordedCall("off"))

    def single_color(self, color: RGB) -> None:
        self.calls.append(RecordedCall("single_color", (color,)))

    def set_ring_colors(self, colors: list[RGB]) -> None:
        self.calls.append(RecordedCall("set_ring_colors", (list(colors),)))

    def breath(self, color: RGB, speed: int = 1, brightness: int = 128) -> None:
        self.calls.append(
            RecordedCall("breath", (color,), {"speed": speed, "brightness": brightness})
        )

    def rainbow(self, speed: int = 1, brightness: int = 128) -> None:
        self.calls.append(
            RecordedCall("rainbow", (), {"speed": speed, "brightness": brightness})
        )

    def doa(self, base_color: RGB, doa_color: RGB) -> None:
        self.calls.append(RecordedCall("doa", (base_color, doa_color)))

    def power_led_ring(self, enabled: bool) -> None:
        self.calls.append(RecordedCall("power_led_ring", (enabled,)))

    def clear(self) -> None:
        self.calls.clear()

    def method_names(self) -> list[str]:
        return [c.method for c in self.calls]


# ============================================================
# Dry-run backend (log only)
# ============================================================

class DryRunBackend(LedRingBackend):
    """Logs all commands without executing anything."""

    def __init__(self, logger: Callable[[str], None] | None = print) -> None:
        self.logger = logger

    def _log(self, msg: str) -> None:
        if self.logger:
            self.logger(f"[DRY RUN] {msg}")

    def off(self) -> None:
        self._log("off")

    def single_color(self, color: RGB) -> None:
        self._log(f"single_color({color})")

    def set_ring_colors(self, colors: list[RGB]) -> None:
        self._log(f"set_ring_colors({len(colors)} leds)")

    def breath(self, color: RGB, speed: int = 1, brightness: int = 128) -> None:
        self._log(f"breath({color}, speed={speed}, brightness={brightness})")

    def rainbow(self, speed: int = 1, brightness: int = 128) -> None:
        self._log(f"rainbow(speed={speed}, brightness={brightness})")

    def doa(self, base_color: RGB, doa_color: RGB) -> None:
        self._log(f"doa({base_color}, {doa_color})")

    def power_led_ring(self, enabled: bool) -> None:
        self._log(f"power_led_ring({enabled})")


# ============================================================
# XVF Host backend (production)
# ============================================================

class XvfHostBackend(LedRingBackend):
    """Concrete backend that talks to xvf_host.exe / xvf_host.py."""

    def __init__(
        self,
        host_path: str | Path,
        python_executable: str | Path | None = None,
        auto_power_on: bool = True,
        auto_enable_gamma: bool = True,
        dry_run: bool = False,
        timeout_seconds: float = 8.0,
        logger: Optional[Callable[[str], None]] = print,
    ) -> None:
        self.host_path = Path(host_path)
        self.python_executable = (
            Path(python_executable) if python_executable else None
        )
        self.auto_power_on = auto_power_on
        self.auto_enable_gamma = auto_enable_gamma
        self.dry_run = dry_run
        self.timeout_seconds = timeout_seconds
        self.logger = logger

        if not self.host_path.exists() and not self.dry_run:
            raise FileNotFoundError(f"xvf_host not found: {self.host_path}")

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger(message)

    def _base_command(self) -> list[str]:
        if self.host_path.suffix.lower() == ".py":
            python_exe = str(self.python_executable or sys.executable)
            return [python_exe, str(self.host_path)]
        return [str(self.host_path)]

    def _run(self, *args: object) -> subprocess.CompletedProcess[str] | None:
        cmd = self._base_command() + [str(arg) for arg in args]

        if self.dry_run:
            self._log("[DRY RUN] " + " ".join(cmd))
            return None

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if result.returncode != 0:
            raise HostCommandError(
                f"Command failed ({result.returncode}): {' '.join(cmd)}\n"
                f"STDOUT: {stdout}\nSTDERR: {stderr}"
            )

        if stdout:
            self._log(stdout)

        return result

    @staticmethod
    def _clamp_uint8(value: int) -> int:
        return max(0, min(255, int(value)))

    def _prepare_ring(self) -> None:
        if self.auto_power_on:
            self.power_led_ring(True)
        if self.auto_enable_gamma:
            self._run("LED_GAMMIFY", 1)

    def power_led_ring(self, enabled: bool) -> None:
        self._run("GPO_WRITE_VALUE", 33, 1 if enabled else 0)

    def off(self) -> None:
        self._prepare_ring()
        self._run("LED_EFFECT", 0)

    def single_color(self, color: RGB) -> None:
        self._prepare_ring()
        self._run("LED_EFFECT", 3)
        self._run("LED_COLOR", color.to_xvf_hex())

    def set_ring_colors(self, colors: list[RGB]) -> None:
        self._prepare_ring()
        self._run("LED_EFFECT", 5)
        hex_colors = [c.to_xvf_hex() for c in colors]
        self._run("LED_RING_COLOR", *hex_colors)

    def breath(self, color: RGB, speed: int = 1, brightness: int = 128) -> None:
        self._prepare_ring()
        self._run("LED_EFFECT", 1)
        self._run("LED_COLOR", color.to_xvf_hex())
        self._run("LED_SPEED", self._clamp_uint8(speed))
        self._run("LED_BRIGHTNESS", self._clamp_uint8(brightness))

    def rainbow(self, speed: int = 1, brightness: int = 128) -> None:
        self._prepare_ring()
        self._run("LED_EFFECT", 2)
        self._run("LED_SPEED", self._clamp_uint8(speed))
        self._run("LED_BRIGHTNESS", self._clamp_uint8(brightness))

    def doa(self, base_color: RGB, doa_color: RGB) -> None:
        self._prepare_ring()
        self._run("LED_EFFECT", 4)
        self._run("LED_DOA_COLOR", base_color.to_xvf_hex(), doa_color.to_xvf_hex())
