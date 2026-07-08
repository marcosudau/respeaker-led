# Sanierungsprotokoll

Stand: 2026-07-08

## Ziel

Das Git-/Projektchaos wird bereinigt, damit `main` wieder der eindeutige weiterentwickelbare Hauptstand ist. Gleichzeitig werden die Analyseergebnisse so dokumentiert, dass die spaetere Weiterentwicklung einen klaren Einstiegspunkt hat.

## Durchgefuehrte Entscheidungen

- `codex/develop-branch` ist der Ausgangsstand fuer die Konsolidierung.
- `main` wird per Fast-Forward auf den bereinigten Develop-Stand gebracht.
- Das Release-Bundle-Verhalten bleibt sicher: Ueberschreiben nur mit `force`.
- `docs/reports/` verwendet Datums-Praefixe fuer sortierbare Dateien.
- Die Effekt-Source-Inkonsistenz in `tools/effect_building/build/sources/` wird als Folgepunkt dokumentiert und nicht durch blindes Cleanup riskiert.
- `tools/effect_building/sorted_by_type/` bleibt als lokaler, ignored Sortier-/Migrationskontext erhalten.

## Sicherheitsnetz

- Backup-Branch: `codex/backup-before-main-cleanup`
- Backup-Tag: `backup-before-main-cleanup-2026-07-08`
- Alter verschmutzter `P:\CodexApp\led_controller_respeaker`-Worktree wurde auf den Backup-Branch `codex/main-worktree-dirty-backup-2026-07-08` umgeschaltet.
- Zusaetzlicher Stash fuer diesen alten Main-Worktree: `pre-main-fast-forward dirty main worktree 2026-07-08`

## Git-Konsolidierung

- Sanierungscommit wurde zuerst auf `codex/develop-branch` erstellt.
- `main` wurde danach lokal auf denselben Commit gebracht.
- Der aktive Arbeitsordner `C:\Users\marco\OneDrive\Desktop\Respeaker_MaterialCheck\led_controller_respeaker` ist danach auf `main`.
- `codex/develop-branch` bleibt vorerst als Sicherungs-/Vergleichsbranch erhalten.
- Alte Branches und Worktrees werden nicht aggressiv geloescht, solange der neue `main` nicht einige Zeit als stabiler Hauptstand bestaetigt ist.

## Validierung

Ausgefuehrte Validierung:

- `uv run pytest tests/test_release_tooling.py -q --basetemp=.pytest_tmp`
  - Ergebnis: `10 passed`
- `uv run python tools\effect_packager.py verify-effect-package tools\effect_building\build\build_lefxset\default-effects.lefxset`
  - Ergebnis: erfolgreich, `kind=effect_set`, `set_id=default-effects`
- `uv run python -c "from src.engine.effect_registry import build_default_effect_registry; r=build_default_effect_registry(); print(...)"`
  - Ergebnis: `EFFECTS 37`, `PRESETS 148`, `COMMANDS 148`
- `uv run pytest -q --basetemp=.pytest_tmp`
  - Ergebnis: `117 passed`
- Service-Smoke im `--no-device`-Modus:
  - Start auf `127.0.0.1:8765`
  - `python main.py ping`: erfolgreich
  - `python main.py list-effects`: erfolgreich
  - `python main.py apply-effect solid_color MAIN_LAYER --params '{"color":"#224466"}'`: erfolgreich
  - `python main.py shutdown`: erfolgreich, Serverprozess beendet

Hinweis:

- Ein parallel gestarteter Registry-Check lief einmal gegen einen Windows-Temp-Cache-Lock in `effect_package_cache` und wurde danach seriell erfolgreich wiederholt. Das war kein reproduzierbarer Testfehler der Codebasis.
