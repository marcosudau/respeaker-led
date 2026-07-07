from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import sys


SCRIPT_ROOT = Path(__file__).resolve().parent
BUILD_TOOLS_ROOT = SCRIPT_ROOT.parent
if str(BUILD_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BUILD_TOOLS_ROOT))

from _build_common import (  # noqa: E402
    BUILD_CONFIG_PATH,
    DEFAULT_RELEASE_BUNDLE_DIR,
    DEFAULT_TEMPLATE_ROOT,
    bundle_archive_name,
    bundle_directory_name,
    discover_builtin_artifacts,
    load_python_version,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create the release bundle zip from the template and the built executable.")
    parser.add_argument("--exe", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_RELEASE_BUNDLE_DIR))
    parser.add_argument("--template-root", default=str(DEFAULT_TEMPLATE_ROOT))
    parser.add_argument("--config", default=str(BUILD_CONFIG_PATH))
    parser.add_argument("--version")
    parser.add_argument("--no-version", action="store_true")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing bundle ZIP and staging directory in the output directory.",
    )
    return parser


def create_release_bundle(
    *,
    exe_path: Path,
    output_dir: Path,
    template_root: Path,
    config_path: Path,
    version: str | None,
    include_version: bool,
    force: bool,
) -> dict[str, object]:
    if not template_root.is_dir():
        raise FileNotFoundError(f"Release template directory does not exist: {template_root}")
    if not exe_path.is_file():
        raise FileNotFoundError(f"Built executable does not exist: {exe_path}")

    resolved_version = (version or load_python_version()).strip().lstrip("v")
    bundle_root_name = bundle_directory_name(version=resolved_version, include_version=include_version)
    archive_name = bundle_archive_name(version=resolved_version, include_version=include_version)
    output_dir.mkdir(parents=True, exist_ok=True)
    staging_root = output_dir / "_staging"
    bundle_root = staging_root / bundle_root_name
    zip_path = output_dir / archive_name

    if zip_path.exists():
        if not force:
            raise FileExistsError(
                f"Release bundle archive already exists: {zip_path}. Re-run with force=True / --force to overwrite it."
            )
        zip_path.unlink()
    if staging_root.exists():
        if not force:
            raise FileExistsError(
                f"Release bundle staging directory already exists: {staging_root}. Re-run with force=True / --force to overwrite it."
            )
        shutil.rmtree(staging_root)

    shutil.copytree(template_root, bundle_root)
    shutil.copy2(exe_path, bundle_root / exe_path.name)

    copied_artifacts: list[str] = []
    for artifact in discover_builtin_artifacts(config_path):
        source_path = Path(artifact["source_path"])
        relative_path = Path(artifact["relative_path"])
        destination_root = "effects" if artifact["kind"] == "effect_set" else "packages"
        destination_path = bundle_root / destination_root / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        copied_artifacts.append(destination_path.relative_to(bundle_root).as_posix())

    default_effect_set = bundle_root / "effects" / "default-effects.lefxset"
    if not default_effect_set.is_file():
        raise FileNotFoundError(
            "Release bundle is missing effects/default-effects.lefxset. "
            "Build the configured effect artifacts before creating the release bundle."
        )

    manifest = {
        "ok": True,
        "version": resolved_version,
        "bundle_root": bundle_root_name,
        "archive_path": str(zip_path),
        "exe_name": exe_path.name,
        "effect_artifacts": sorted(copied_artifacts),
    }
    (bundle_root / "bundle_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    archive_base = zip_path.with_suffix("")
    shutil.make_archive(str(archive_base), "zip", root_dir=staging_root, base_dir=bundle_root_name)
    shutil.rmtree(staging_root, ignore_errors=True)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = create_release_bundle(
        exe_path=Path(args.exe).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        template_root=Path(args.template_root).resolve(),
        config_path=Path(args.config).resolve(),
        version=args.version,
        include_version=not args.no_version,
        force=args.force,
    )
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
