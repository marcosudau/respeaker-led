"""RGB color representation and named color palette."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RGB:
    """Immutable RGB color with channel validation (0–255)."""

    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        for channel in ("r", "g", "b"):
            value = getattr(self, channel)
            if not isinstance(value, int) or not 0 <= value <= 255:
                raise ValueError(
                    f"RGB channel '{channel}' must be int 0..255, got {value!r}"
                )

    # -- Serialisation helpers ----------------------------------------

    def to_hex(self) -> str:
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    def to_xvf_hex(self) -> str:
        return f"0x{self.r:02X}{self.g:02X}{self.b:02X}"

    def to_tuple(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)

    # -- Colour math --------------------------------------------------

    def scaled(self, factor: float) -> RGB:
        factor = max(0.0, min(1.0, factor))
        return RGB(
            int(self.r * factor),
            int(self.g * factor),
            int(self.b * factor),
        )

    def blend(self, other: RGB, ratio: float) -> RGB:
        ratio = max(0.0, min(1.0, ratio))
        inv = 1.0 - ratio
        return RGB(
            int(self.r * inv + other.r * ratio),
            int(self.g * inv + other.g * ratio),
            int(self.b * inv + other.b * ratio),
        )

    # -- Factory class methods ----------------------------------------

    @classmethod
    def from_tuple(cls, values: tuple | list) -> RGB:
        if len(values) != 3:
            raise ValueError(f"Expected 3 values, got {len(values)}")
        return cls(int(values[0]), int(values[1]), int(values[2]))

    @classmethod
    def from_hex(cls, value: str) -> RGB:
        s = value.strip()
        if s.startswith("#"):
            s = s[1:]
        elif s.lower().startswith("0x"):
            s = s[2:]
        if len(s) != 6:
            raise ValueError(f"Cannot parse hex color: {value!r}")
        try:
            return cls(int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except ValueError:
            raise ValueError(f"Cannot parse hex color: {value!r}") from None


# ============================================================
# Predefined colour palette
# ============================================================

class Colors:
    BLACK = RGB(0, 0, 0)
    WHITE = RGB(255, 255, 255)

    RED = RGB(255, 0, 0)
    GREEN = RGB(0, 255, 0)
    BLUE = RGB(0, 90, 255)
    CYAN = RGB(0, 220, 255)
    YELLOW = RGB(255, 180, 0)
    ORANGE = RGB(255, 100, 0)
    PURPLE = RGB(180, 0, 255)
    PINK = RGB(255, 0, 150)

    SOFT_GREEN = RGB(0, 160, 60)
    SOFT_BLUE = RGB(0, 100, 180)
    SOFT_CYAN = RGB(0, 140, 180)
    SOFT_RED = RGB(180, 0, 0)
    SOFT_YELLOW = RGB(180, 120, 0)
    SOFT_PURPLE = RGB(110, 0, 160)


NAMED_COLORS: dict[str, RGB] = {
    "black": Colors.BLACK,
    "white": Colors.WHITE,
    "red": Colors.RED,
    "green": Colors.GREEN,
    "blue": Colors.BLUE,
    "cyan": Colors.CYAN,
    "yellow": Colors.YELLOW,
    "orange": Colors.ORANGE,
    "purple": Colors.PURPLE,
    "pink": Colors.PINK,
    "soft_green": Colors.SOFT_GREEN,
    "soft_blue": Colors.SOFT_BLUE,
    "soft_cyan": Colors.SOFT_CYAN,
    "soft_red": Colors.SOFT_RED,
    "soft_yellow": Colors.SOFT_YELLOW,
    "soft_purple": Colors.SOFT_PURPLE,
}
