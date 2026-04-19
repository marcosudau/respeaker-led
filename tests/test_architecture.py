from __future__ import annotations

from pathlib import Path

from tests.build_artifact_helpers import default_effect_set_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"


def test_core_source_has_no_legacy_widget_or_quick_action_imports():
    legacy_markers = [
        "widget_loader",
        "quick_actions_layer",
        "list-widgets",
        "/api/v1/widgets",
        "/api/v1/quick-actions",
        "/api/v1/work",
        "/api/v1/state-layer/visual",
        "/api/v1/main-layer/visual",
        "/api/v1/event-layer",
        "serve-api",
        "push-event",
        "showcase_app",
        "standard_effect_library",
    ]

    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for marker in legacy_markers:
            assert marker not in text, f"Found legacy marker {marker!r} in {path}"


def test_builtin_effects_are_configured_outside_src():
    assert (PROJECT_ROOT / "build-tools" / "build_config.json").is_file()
    assert default_effect_set_path().is_file()
    assert not (SRC_ROOT / "led_effects" / "effects" / "default-effects.lefxset").exists()
    assert not (SRC_ROOT / "builtin_effects.py").exists()
