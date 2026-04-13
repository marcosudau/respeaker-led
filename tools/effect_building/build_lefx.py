from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


if __package__ in {None, ""}:
    _PROJECT_ROOT = Path(__file__).resolve().parents[2]
    _PROJECT_ROOT_STR = str(_PROJECT_ROOT)
    if _PROJECT_ROOT_STR not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT_STR)
    __package__ = "tools.effect_building"

from .standard_effects import DEFAULT_LEFX_ROOT, DEFAULT_SOURCES_ROOT, build_standard_effect_packages, discover_standard_effects


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and build standalone .lefx packages for the standard effects")
    parser.add_argument("--sources-root", default=str(DEFAULT_SOURCES_ROOT))
    parser.add_argument("--output-root", default=str(DEFAULT_LEFX_ROOT))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    sources_root = Path(args.sources_root)
    output_root = Path(args.output_root)
    packages = build_standard_effect_packages(sources_root, output_root)
    payload = {
        "ok": True,
        "kind": "lefx_build",
        "sources_root": str(sources_root),
        "output_root": str(output_root),
        "effect_count": len(packages),
        "effect_ids": [spec.effect_id for spec in discover_standard_effects()],
        "packages": [str(path) for path in packages],
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())