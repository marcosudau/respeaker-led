from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
TEST_CACHE_ROOT = PROJECT_ROOT / "tests" / ".cache"
_ORIGINAL_EFFECT_BUILD_ROOT = os.environ.get("LED_CONTROLLER_EFFECT_BUILD_ROOT")
_ORIGINAL_DEFAULT_EFFECT_SET = os.environ.get("LED_CONTROLLER_DEFAULT_EFFECT_SET")
_ORIGINAL_PYCACHE_PREFIX = sys.pycache_prefix

for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    TEST_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    if config.option.basetemp is None:
        config.option.basetemp = str(TEST_CACHE_ROOT / "tmp")

    effect_build_root = TEST_CACHE_ROOT / "effect_build"
    os.environ.setdefault("LED_CONTROLLER_EFFECT_BUILD_ROOT", str(effect_build_root))
    os.environ.setdefault(
        "LED_CONTROLLER_DEFAULT_EFFECT_SET",
        str(effect_build_root / "output" / "default-effects.lefxset"),
    )
    sys.pycache_prefix = str(TEST_CACHE_ROOT / "pycache")


def pytest_unconfigure(config: pytest.Config) -> None:
    del config
    sys.pycache_prefix = _ORIGINAL_PYCACHE_PREFIX
    _restore_environment("LED_CONTROLLER_EFFECT_BUILD_ROOT", _ORIGINAL_EFFECT_BUILD_ROOT)
    _restore_environment("LED_CONTROLLER_DEFAULT_EFFECT_SET", _ORIGINAL_DEFAULT_EFFECT_SET)
    shutil.rmtree(TEST_CACHE_ROOT, ignore_errors=True)
    cache_dirs = [PROJECT_ROOT / "__pycache__"]
    for source_root in ("src", "tests", "tools", "build-tools"):
        cache_dirs.extend((PROJECT_ROOT / source_root).rglob("__pycache__"))
    for cache_dir in cache_dirs:
        shutil.rmtree(cache_dir, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def ensure_builtin_effect_artifacts() -> None:
    from tools.effect_building.standard_effects import (
        DEFAULT_LEFXSET_ROOT,
        build_standard_effect_packages,
        build_standard_effect_set,
    )

    default_effect_set = DEFAULT_LEFXSET_ROOT / "default-effects.lefxset"
    if default_effect_set.is_file():
        return
    build_standard_effect_packages()
    build_standard_effect_set()


def _restore_environment(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
