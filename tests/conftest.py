from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tools.effect_building.standard_effects import build_standard_effect_packages, build_standard_effect_set


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)


@pytest.fixture(scope="session", autouse=True)
def ensure_builtin_effect_artifacts() -> None:
    default_effect_set = PROJECT_ROOT / "tools" / "effect_building" / "build" / "build_lefxset" / "default-effects.lefxset"
    if default_effect_set.is_file():
        return
    build_standard_effect_packages()
    build_standard_effect_set()
