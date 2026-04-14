from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EFFECT_BUILDING_ROOT = PROJECT_ROOT / "tools" / "effect_building"
RELEASE_TEMPLATE_ROOT = PROJECT_ROOT / "release" / "led_controller_service_release_1"

ROOT_DIR_TARGETS = (
    ("build", "PyInstaller build directory"),
    ("dist", "PyInstaller distribution directory"),
    ("artifacts", "assembled release bundle artifacts"),
    ("logs", "root-level runtime logs"),
    (".pytest_tmp", "pytest temporary directory"),
)

ROOT_FILE_TARGETS = (
    ("src/led_effects/default-effects.lefxset", "published default .lefxset build output"),
    ("src/led_effects/effects/default-effects.lefxset", "development default .lefxset build output"),
    ("release/led_controller_service_release_1.zip", "packaged release archive"),
)

RELEASE_TEMPLATE_TARGETS = (
    ("led_controller_service.exe", "built executable copied into the release template"),
    ("bundle_manifest.json", "assembled release manifest"),
    ("effects", "copied effect artifacts inside the release template"),
    ("packages", "copied package artifacts inside the release template"),
    ("logs", "release template runtime logs"),
    ("runtime_state", "release template runtime state and effect cache"),
    ("__pycache__", "release template Python bytecode cache"),
)

EFFECT_BUILD_ROOT_PREFIXES = ("build_lefx", "build_lefxset")


@dataclass(frozen=True)
class CleanupTarget:
    path: Path
    kind: str
    reason: str

    def to_payload(self, project_root: Path) -> dict[str, str]:
        return {
            "path": str(self.path.relative_to(project_root).as_posix()),
            "kind": self.kind,
            "reason": self.reason,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or remove generated build artifacts so the repository can be rebuilt from a clean state."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete the discovered build artifacts. Without this flag the script only reports them.",
    )
    return parser


def collect_cleanup_targets(project_root: Path = PROJECT_ROOT) -> list[CleanupTarget]:
    root = project_root.resolve()
    candidates: list[CleanupTarget] = []

    for relative_path, reason in ROOT_DIR_TARGETS:
        target = root / relative_path
        if target.exists():
            candidates.append(CleanupTarget(path=target, kind="dir", reason=reason))

    for relative_path, reason in ROOT_FILE_TARGETS:
        target = root / relative_path
        if target.exists():
            candidates.append(CleanupTarget(path=target, kind="file", reason=reason))

    candidates.extend(_discover_effect_build_targets(root))
    candidates.extend(_discover_release_template_targets(root))

    return _dedupe_targets(root, candidates)


def reset_build_artifacts(*, project_root: Path = PROJECT_ROOT, apply: bool = False) -> dict[str, object]:
    root = project_root.resolve()
    targets = collect_cleanup_targets(root)
    removed: list[CleanupTarget] = []

    if apply:
        for target in sorted(targets, key=lambda item: (item.path.is_file(), len(item.path.parts)), reverse=True):
            if target.kind == "dir":
                shutil.rmtree(target.path)
            else:
                target.path.unlink()
            removed.append(target)

    return {
        "ok": True,
        "mode": "apply" if apply else "dry-run",
        "project_root": str(root),
        "target_count": len(targets),
        "targets": [target.to_payload(root) for target in targets],
        "removed": [target.to_payload(root) for target in removed],
    }


def _discover_effect_build_targets(project_root: Path) -> list[CleanupTarget]:
    effect_root = project_root / "tools" / "effect_building"
    if not effect_root.exists():
        return []

    targets: list[CleanupTarget] = []
    for child in sorted(effect_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name in {"sources", "_generated"}:
            continue
        if child.name.startswith(EFFECT_BUILD_ROOT_PREFIXES):
            targets.append(CleanupTarget(path=child, kind="dir", reason="generated .lefx/.lefxset build directory"))

    generated_sources = effect_root / "sources" / "default-effects"
    if generated_sources.exists():
        targets.append(CleanupTarget(path=generated_sources, kind="dir", reason="generated effect source staging area"))

    generated_set = effect_root / "_generated" / "default-effects_set"
    if generated_set.exists():
        targets.append(CleanupTarget(path=generated_set, kind="dir", reason="generated .lefxset work directory"))

    return targets


def _discover_release_template_targets(project_root: Path) -> list[CleanupTarget]:
    release_root = project_root / "release" / "led_controller_service_release_1"
    if not release_root.exists():
        return []

    targets: list[CleanupTarget] = []
    for relative_path, reason in RELEASE_TEMPLATE_TARGETS:
        target = release_root / relative_path
        if target.exists():
            kind = "dir" if target.is_dir() else "file"
            targets.append(CleanupTarget(path=target, kind=kind, reason=reason))

    for zip_path in sorted(release_root.glob("*.zip")):
        targets.append(CleanupTarget(path=zip_path, kind="file", reason="release template archive"))

    return targets


def _dedupe_targets(project_root: Path, targets: list[CleanupTarget]) -> list[CleanupTarget]:
    kept: list[CleanupTarget] = []

    for target in sorted(targets, key=lambda item: (len(item.path.parts), str(item.path).lower())):
        resolved = target.path.resolve()
        if not _is_within_root(resolved, project_root):
            raise ValueError(f"Refusing to delete path outside the project root: {resolved}")
        if any(_is_parent_path(existing.path.resolve(), resolved) for existing in kept if existing.kind == "dir"):
            continue
        kept.append(CleanupTarget(path=resolved, kind=target.kind, reason=target.reason))

    return sorted(kept, key=lambda item: item.path.relative_to(project_root).as_posix())


def _is_parent_path(parent: Path, child: Path) -> bool:
    return parent == child or parent in child.parents


def _is_within_root(path: Path, project_root: Path) -> bool:
    return path == project_root or project_root in path.parents


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = reset_build_artifacts(apply=args.apply)
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
