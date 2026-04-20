from __future__ import annotations

import sys
from pathlib import Path


BUILD_TOOLS_ROOT = Path(SPECPATH).resolve()
if str(BUILD_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BUILD_TOOLS_ROOT))

from pyinstaller_support import build_datas, build_excludes, build_hiddenimports, exe_stem  # noqa: E402


PROJECT_ROOT = BUILD_TOOLS_ROOT.parent
datas = build_datas()
excludes = build_excludes()
hiddenimports = build_hiddenimports()
exe_name = exe_stem()

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    hookspath=[str(BUILD_TOOLS_ROOT / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)
