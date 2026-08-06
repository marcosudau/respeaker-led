from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from respeaker_led.interfaces.cli import build_parser


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = PROJECT_ROOT / "docs"
ARCHIVE_ROOT = DOCS_ROOT / ".archive"
PLANNING_ROOT = DOCS_ROOT / ".planning"

CHAPTERS = (
    "01_overview.md",
    "02_vocabulary.md",
    "03_layers_and_composition.md",
    "04_effect_types_and_lifecycles.md",
    "05_schema_v2.md",
    "06_parameters_and_values.md",
    "07_runtime_inputs.md",
    "08_packages_ids_and_configuration.md",
    "09_control_interface.md",
    "10_validation_and_build.md",
    "11_architecture_boundaries.md",
    "12_status_and_outlook.md",
)

ARCHIVED_PATHS = (
    "effect-concepts/für_historie_wichtitige_dokumente/Das_Finale_Effekte-Modell.md",
    "effect-concepts/für_historie_wichtitige_dokumente/DoA_Konzept_Integration_und_Template.md",
    "effect-concepts/für_historie_wichtitige_dokumente/Effekte-Bedeutung_System_Beispiele.md",
    "effect-concepts/für_historie_wichtitige_dokumente/history_doc_led_controller_respeaker.md",
    "effect-concepts/für_historie_wichtitige_dokumente/konzept_lefx_dateien/08__13_konzept_lefx_dateien.md",
    "effect-concepts/lefx_schema_v2_implemented_baseline.md",
    "project-history/development/dev_notes.md",
    "project-history/development/runtime_layers.md",
    "project-history/documentation-restructure/effect_system_documentation_roadmap.md",
    "project-history/history_and_legacy/history_doc_led_controller_respeaker.md",
    "project-history/planning/01_zielarchitektur.md",
    "project-history/planning/11_konzept_DoA_integration_und_template.md",
    "project-history/replaced-current-docs/current_approach.md",
    "project-history/replaced-current-docs/effects_before_reference.md",
    "project-history/replaced-current-docs/presets.md",
    "project-history/sanitation-reports/2026-07-08_git_sanierungsplan.md",
    "project-history/sanitation-reports/2026-07-28_konsolidierungsabschluss.md",
)

HISTORICAL_CONCEPT_FILES = (
    "08__02_konzept_lefx_dateien.md",
    "08__04_final_konzept_lefx_dateien.md",
    "08__04_konzept_lefx_dateien.md",
    "08__05_konzept_lefx_dateien.md",
    "08__06_konzept_lefx_dateien.md",
    "08__07_konzept_lefx_dateien.md",
    "08__08_konzept_lefx_dateien.md",
    "08__09_konzept_lefx_dateien.md",
    "08__10_konzept_lefx_dateien.md",
    "08__11_konzept_lefx_dateien.md",
    "08__12_konzept_lefx_dateien.md",
    "08__13_konzept_lefx_dateien.md",
)


def test_effect_system_contains_the_complete_ordered_reference():
    root = DOCS_ROOT / "effect-system"

    assert (root / "README.md").is_file()
    assert tuple(path.name for path in sorted(root.glob("[0-9][0-9]_*.md"))) == CHAPTERS


def test_current_documentation_has_no_broken_relative_markdown_links():
    markdown_files = [
        PROJECT_ROOT / "README.md",
        *(
            path
            for path in DOCS_ROOT.rglob("*.md")
            if ARCHIVE_ROOT not in path.parents
        ),
    ]
    failures: list[str] = []
    pattern = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)")

    for source in markdown_files:
        for match in pattern.finditer(source.read_text(encoding="utf-8")):
            target = unquote(match.group(1))
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (source.parent / target).resolve()
            if not resolved.exists():
                failures.append(
                    f"{source.relative_to(PROJECT_ROOT)} -> {target}"
                )

    assert failures == []


def test_legacy_documentation_is_archived_and_not_mixed_with_current_docs():
    for relative_path in ARCHIVED_PATHS:
        assert (ARCHIVE_ROOT / relative_path).is_file()

    assert not (DOCS_ROOT / "archive").exists()
    assert not (DOCS_ROOT / "current_approach.md").exists()
    assert not (DOCS_ROOT / "presets.md").exists()
    assert not (DOCS_ROOT / "reports").exists()
    assert not (DOCS_ROOT / "history_and_legacy").exists()
    assert not (DOCS_ROOT / "planning").exists()


def test_historical_concept_files_are_preserved_with_content():
    concept_root = (
        ARCHIVE_ROOT
        / "effect-concepts"
        / "für_historie_wichtitige_dokumente"
        / "konzept_lefx_dateien"
    )
    present = {path.name for path in concept_root.glob("*.md")}

    assert set(HISTORICAL_CONCEPT_FILES) <= present
    for name in HISTORICAL_CONCEPT_FILES:
        assert (concept_root / name).is_file()
        assert (concept_root / name).read_bytes() != b""


def test_active_planning_contains_only_current_plans():
    planning_files = {
        path.relative_to(PLANNING_ROOT).as_posix()
        for path in PLANNING_ROOT.rglob("*.md")
    }

    assert planning_files == {
        "index.md",
        "smartspeaker_set.md",
        "v3/README.md",
        "v3/lifecycle_hooks.md",
    }


def test_cli_reference_covers_every_implemented_subcommand():
    parser = build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if action.__class__.__name__ == "_SubParsersAction"
    )
    reference = (DOCS_ROOT / "cli_guide.md").read_text(encoding="utf-8")

    missing = [
        command
        for command in sorted(subparsers.choices)
        if f"`{command}`" not in reference
    ]

    assert missing == []


def test_api_reference_covers_every_implemented_route():
    source = (PROJECT_ROOT / "src" / "respeaker_led" / "interfaces" / "api.py").read_text(
        encoding="utf-8"
    )
    implemented_routes = {
        path
        for _, path in re.findall(
            r'@app\.(get|post|delete)\("([^"]+)"',
            source,
        )
    }
    reference = (DOCS_ROOT / "api_guide.md").read_text(encoding="utf-8")
    missing = sorted(
        route
        for route in implemented_routes
        if route not in reference
    )

    assert missing == []
