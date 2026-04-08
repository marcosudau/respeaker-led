from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
LED_EFFECTS_ROOT = PROJECT_ROOT / "led_effects"
PRESET_PACKS_ROOT = LED_EFFECTS_ROOT / "preset_packs"
DOCS_ROOT = PROJECT_ROOT / "docs"
TESTS_ROOT = PROJECT_ROOT / "tests"
XVF_HOST_PATH = PROJECT_ROOT / "python_control" / "xvf_host.py"
