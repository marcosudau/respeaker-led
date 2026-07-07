"""Core package for the reSpeaker LED controller service."""

from __future__ import annotations

import importlib.util
from importlib.metadata import PackageNotFoundError, version as metadata_version
from pathlib import Path


def _load_version() -> str:
    version_path = Path(__file__).resolve().parents[1] / "build-tools" / "version.py"
    if version_path.is_file():
        spec = importlib.util.spec_from_file_location("build_tools_version", version_path)
        if spec is not None and spec.loader is not None:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            version = getattr(module, "__version__", None)
            if isinstance(version, str) and version.strip():
                return version

    try:
        return metadata_version(__package__ or __name__)
    except PackageNotFoundError:
        return "0+unknown"


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
