from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from src.engine.effect_package_builder import build_effect_package, build_effect_set
from src.engine.effect_package_loader import inspect_effect_source, verify_effect_source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and inspect packaged LED effect artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pack_effect = subparsers.add_parser("pack-effect", help="Build a .lefx package from an effect source directory")
    pack_effect.add_argument("source_dir")
    pack_effect.add_argument("output_file")
    pack_effect.set_defaults(command_kind="pack_effect")

    pack_effect_set = subparsers.add_parser("pack-effect-set", help="Build a .lefxset package from an effect set source directory")
    pack_effect_set.add_argument("source_dir")
    pack_effect_set.add_argument("output_file")
    pack_effect_set.set_defaults(command_kind="pack_effect_set")

    inspect_parser = subparsers.add_parser("inspect-effect-package", help="Inspect a .lefx or .lefxset package")
    inspect_parser.add_argument("package_file")
    inspect_parser.set_defaults(command_kind="inspect")

    verify_parser = subparsers.add_parser("verify-effect-package", help="Verify a .lefx or .lefxset package")
    verify_parser.add_argument("package_file")
    verify_parser.set_defaults(command_kind="verify")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command_kind == "pack_effect":
        artifact = build_effect_package(args.source_dir, args.output_file)
        print(json.dumps({"ok": True, "kind": artifact.kind, "identifier": artifact.identifier, "output_path": str(artifact.output_path)}, ensure_ascii=True))
        return 0

    if args.command_kind == "pack_effect_set":
        artifact = build_effect_set(args.source_dir, args.output_file)
        print(json.dumps({"ok": True, "kind": artifact.kind, "identifier": artifact.identifier, "output_path": str(artifact.output_path)}, ensure_ascii=True))
        return 0

    if args.command_kind == "inspect":
        print(json.dumps(inspect_effect_source(args.package_file), ensure_ascii=True, indent=2, sort_keys=True))
        return 0

    if args.command_kind == "verify":
        result = verify_effect_source(args.package_file)
        print(json.dumps({
            "ok": result.ok,
            "kind": result.kind,
            "source_id": result.source_id,
            "package_id": result.package_id,
            "set_id": result.set_id,
            "effect_ids": list(result.effect_ids),
            "command_names": list(result.command_names),
        }, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result.ok else 1

    parser.error(f"Unsupported command kind: {args.command_kind}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
