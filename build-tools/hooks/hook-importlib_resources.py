from __future__ import annotations

import importlib.util

from PyInstaller.utils.hooks import check_requirement, collect_data_files


if check_requirement("importlib_resources < 1.2.0"):
    datas = collect_data_files("importlib_resources", includes=["version.txt"])
else:
    datas = []


hiddenimports: list[str] = []
if check_requirement("importlib_resources >= 1.3.1"):
    if importlib.util.find_spec("importlib_resources.trees") is not None:
        hiddenimports = ["importlib_resources.trees"]
