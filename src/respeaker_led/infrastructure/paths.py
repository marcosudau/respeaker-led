from __future__ import annotations

import sys
import tempfile
from pathlib import Path


def _resolve_resource_root(package_root: Path) -> Path:
    """Resolve the directory that resources are looked up relative to.

    Three deployment shapes have to be told apart:
    PyInstaller unpacks everything into ``sys._MEIPASS``; a source checkout keeps
    resources next to the repository root above ``src/``; an installed wheel only
    ships the package directory itself.
    """
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root).resolve()

    src_root = package_root.parent
    if src_root.name == "src" and (src_root.parent / "pyproject.toml").is_file():
        return src_root.parent

    return package_root


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
RESOURCE_ROOT = _resolve_resource_root(PACKAGE_ROOT)
PROJECT_ROOT = RESOURCE_ROOT
APP_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else PROJECT_ROOT
BUILD_TOOLS_ROOT = RESOURCE_ROOT / "build-tools"
BUILD_CONFIG_PATH = BUILD_TOOLS_ROOT / "build_config.json"
APP_EFFECTS_ROOT = APP_ROOT / "effects"
APP_EFFECT_PACKAGES_ROOT = APP_ROOT / "packages"
SOURCE_ROOT = PROJECT_ROOT / "src" / "respeaker_led"
PACKAGED_EFFECTS_ROOT = PACKAGE_ROOT / "effects"


DEFAULT_EFFECT_SOURCE_ID = "default-effects"
DEFAULT_EFFECT_SET_FILENAME = "default-effects.lefxset"
APP_DEFAULT_EFFECT_SET_PATH = APP_EFFECTS_ROOT / DEFAULT_EFFECT_SET_FILENAME
PACKAGED_DEFAULT_EFFECT_SET_PATH = PACKAGED_EFFECTS_ROOT / DEFAULT_EFFECT_SET_FILENAME

TEMP_DIR = Path(tempfile.gettempdir())
RUNTIME_STATE_ROOT = TEMP_DIR / "respeaker_led_controller_runtime_state"
EFFECT_PACKAGE_CACHE_ROOT = RUNTIME_STATE_ROOT / "effect_package_cache"
BACKGROUND_STATE_FILE = RUNTIME_STATE_ROOT / "background_state.json"
ACTIVE_SERVICE_FILE = RUNTIME_STATE_ROOT / "active_service.json"

LOGS_ROOT = APP_ROOT / "logs"
SERVICE_LOG_FILE = LOGS_ROOT / "led_controller.log"
DOCS_ROOT = RESOURCE_ROOT / "docs"
TESTS_ROOT = RESOURCE_ROOT / "tests"
XVF_HOST_PATH = PACKAGE_ROOT / "python_control" / "xvf_host.py"
