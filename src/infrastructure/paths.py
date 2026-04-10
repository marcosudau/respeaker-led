from __future__ import annotations

import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", PACKAGE_ROOT.parent)).resolve()
PROJECT_ROOT = RESOURCE_ROOT
APP_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else PROJECT_ROOT
SOURCE_ROOT = PROJECT_ROOT / "src"
LED_EFFECTS_ROOT = SOURCE_ROOT / "led_effects"
EFFECTS_LIBRARY_ROOT = LED_EFFECTS_ROOT / "effects"
PRESET_PACKS_ROOT = LED_EFFECTS_ROOT / "preset_packs"
RUNTIME_STATE_ROOT = APP_ROOT / "runtime_state"
BACKGROUND_STATE_FILE = RUNTIME_STATE_ROOT / "background_state.json"
ACTIVE_SERVICE_FILE = RUNTIME_STATE_ROOT / "active_service.json"
LOGS_ROOT = APP_ROOT / "logs"
SERVICE_LOG_FILE = LOGS_ROOT / "led_controller.log"
DOCS_ROOT = RESOURCE_ROOT / "docs"
TESTS_ROOT = RESOURCE_ROOT / "tests"
XVF_HOST_PATH = SOURCE_ROOT / "python_control" / "xvf_host.py"
