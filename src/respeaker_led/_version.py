"""Single source of truth for the package version.

Lives inside the package so that the value is identical in a source checkout, an
installed wheel and the frozen executable. hatchling reads it at build time via
[tool.hatch.version], the build tooling reads it via build-tools/_build_common.py.
"""

from __future__ import annotations


__version__ = "0.1.3"
