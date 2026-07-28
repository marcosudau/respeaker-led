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

from .standard_effects import (
    DEFAULT_BUILD_CACHE_ROOT,
    DEFAULT_LEFX_ROOT,
    DEFAULT_LEFXSET_ROOT,
    DEFAULT_PUBLISH_COPY,
    build_standard_effect_packages,
    build_standard_effect_set,
    cleanup_standard_build_cache,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bundle built .lefx packages into the default-effects .lefxset artifact")
    parser.add_argument("--packages-root", default=str(DEFAULT_LEFX_ROOT))
    parser.add_argument("--output-root", default=str(DEFAULT_LEFXSET_ROOT))
    parser.add_argument("--publish-copy", default=str(DEFAULT_PUBLISH_COPY))
    parser.add_argument("--rebuild-packages", action="store_true")
    parser.add_argument("--keep-cache", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    package_root = Path(args.packages_root)
    output_root = Path(args.output_root)
    publish_copy = None if not args.publish_copy else Path(args.publish_copy)

    if args.rebuild_packages:
        build_standard_effect_packages(output_root=package_root)

    effect_set_path = build_standard_effect_set(package_root, output_root, publish_copy=publish_copy)
    cache_cleaned = False
    if (
        not args.keep_cache
        and package_root.resolve() == DEFAULT_LEFX_ROOT.resolve()
        and output_root.resolve() == DEFAULT_LEFXSET_ROOT.resolve()
    ):
        cleanup_standard_build_cache(DEFAULT_BUILD_CACHE_ROOT)
        cache_cleaned = True
    payload = {
        "ok": True,
        "kind": "lefxset_build",
        "packages_root": str(package_root),
        "output_root": str(output_root),
        "effect_set": str(effect_set_path),
        "publish_copy": None if publish_copy is None else str(publish_copy),
        "cache_cleaned": cache_cleaned,
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
