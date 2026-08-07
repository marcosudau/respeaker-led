"""Core package for the reSpeaker LED controller service."""

from __future__ import annotations

from ._version import __version__
from .services.service import ControllerService

__all__ = [
    "__version__",
    "ControllerService",
    "core",
    "engine",
    "infrastructure",
    "integrations",
    "interfaces",
    "python_control",
    "services",
]

