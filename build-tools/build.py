from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from _build_common import (
    BUILD_CONFIG_PATH,
    PROJECT_ROOT,
    bundle_archive_name,
    load_build_config,
    load_python_version,
    versioned_exe_name,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the complete configured build pipeline.")
    parser.add_argument("--config", default=str(BUILD_CONFIG_PATH))
    parser.add_argument("--no-version", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser


def run_build(*, config_path: Path, include_version: bool, force: bool) -> dict[str, object]:
    config = load_build_config(config_path)
    version = load_python_version()
    spec_file = config_path.parent.parent / str(config.get("spec_file", "build-tools/led_controller_service.spec"))
    exe_name = versioned_exe_name(version=version, include_version=include_version)
    exe_path = PROJECT_ROOT / "dist" / exe_name
    bundle_name = bundle_archive_name(version=version, include_version=include_version)
    bundle_path = PROJECT_ROOT / "dist" / "release_bundle" / bundle_name

    commands: list[list[str]] = []

    if bool(config.get("build_effects", False)):
        commands.append([sys.executable, "tools/effect_building/build_lefxset.py", "--rebuild-packages"])

    if bool(config.get("build_exe", False)):
        env = os.environ.copy()
        env["LED_CONTROLLER_EXE_NAME"] = Path(exe_name).stem
        pyinstaller_cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            str(spec_file),
            "--noconfirm",
            "--distpath",
            "dist",
            "--workpath",
            "build",
        ]
        _run(pyinstaller_cmd, env=env)
        commands.append(pyinstaller_cmd)

        check_exe_cmd = [sys.executable, "build-tools/scripts/check_exe.py", str(exe_path)]
        _run(check_exe_cmd)
        commands.append(check_exe_cmd)

    if bool(config.get("build_release_bundle", False)):
        create_bundle_cmd = [
            sys.executable,
            "build-tools/scripts/create_release_bundle.py",
            "--exe",
            str(exe_path),
            "--output-dir",
            "dist/release_bundle",
            "--config",
            str(config_path),
        ]
        if force:
            create_bundle_cmd.append("--force")
        if not include_version:
            create_bundle_cmd.append("--no-version")
        _run(create_bundle_cmd)
        commands.append(create_bundle_cmd)

        check_bundle_cmd = [sys.executable, "build-tools/scripts/check_release_bundle.py", str(bundle_path)]
        _run(check_bundle_cmd)
        commands.append(check_bundle_cmd)

    if bool(config.get("cleanup", False)):
        cleanup_cmd = [sys.executable, "build-tools/scripts/cleanup_after_build.py"]
        _run(cleanup_cmd)
        commands.append(cleanup_cmd)

    return {
        "ok": True,
        "config_path": str(config_path),
        "version": version,
        "include_version": include_version,
        "artifacts": {
            "exe": str(exe_path),
            "release_bundle": str(bundle_path),
        },
        "commands": commands,
    }


def _run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        env=env,
        check=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_build(
        config_path=Path(args.config).resolve(),
        include_version=not args.no_version,
        force=args.force,
    )
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
