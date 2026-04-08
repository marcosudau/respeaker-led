"""Named effect registry with group queries and merging."""
from __future__ import annotations

from .effects import LedEffect


class EffectRegistry:
    """Map human-readable names to *LedEffect* instances."""

    def __init__(self, effects: dict[str, LedEffect] | None = None) -> None:
        self._effects: dict[str, LedEffect] = dict(effects or {})

    # -- mutation -----------------------------------------------------

    def register(self, name: str, effect: LedEffect) -> None:
        self._effects[name] = effect

    def unregister(self, name: str) -> None:
        self._effects.pop(name, None)

    # -- query --------------------------------------------------------

    def get(self, name: str) -> LedEffect:
        try:
            return self._effects[name]
        except KeyError:
            available = ", ".join(sorted(self._effects))
            raise KeyError(
                f"Unknown effect '{name}'. Available: {available}"
            ) from None

    def has(self, name: str) -> bool:
        return name in self._effects

    def list_names(self) -> list[str]:
        return sorted(self._effects)

    def list_by_group(self, prefix: str) -> list[str]:
        return sorted(n for n in self._effects if n.startswith(prefix))

    # -- bulk ---------------------------------------------------------

    def merge(self, other: EffectRegistry, *, overwrite: bool = False) -> None:
        for name, effect in other._effects.items():
            if overwrite or name not in self._effects:
                self._effects[name] = effect

    def copy(self) -> EffectRegistry:
        return EffectRegistry(dict(self._effects))

    # -- dunder -------------------------------------------------------

    def __len__(self) -> int:
        return len(self._effects)

    def __contains__(self, name: object) -> bool:
        return name in self._effects

    def __iter__(self):
        return iter(sorted(self._effects))

    def __repr__(self) -> str:
        return f"EffectRegistry({len(self._effects)} effects)"
