"""Core package for the reSpeaker LED controller service."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_version() -> str:
    version_path = Path(__file__).resolve().parents[1] / "build-tools" / "version.py"
    spec = importlib.util.spec_from_file_location("build_tools_version", version_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load version from {version_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    version = getattr(module, "__version__", None)
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError(f"Invalid __version__ in {version_path}")
    return version


__version__ = _load_version()

__all__ = [
    "__version__",
    "core",
    "engine",
    "infrastructure",
    "integrations",
    "interfaces",
    "python_control",
    "services",
]
