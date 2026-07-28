# Konsolidierungsabschluss vom 2026-07-28

## Ergebnis

Der neue kanonische Arbeitsstand ist ein frischer GitHub-Klon:

`C:\Users\marco\source\repos\led_controller_respeaker`

Remote:

`https://github.com/marcosudau/led_controller_respeaker.git`

Der Klon wurde direkt aus `origin/main` erstellt. Ausgangspunkt der Aktion war Commit
`213027221392deb1e9683cb8ca201906e16219f3`. Im neuen Klon wird ausschliesslich auf
`main` gearbeitet. Die drei noch auf GitHub vorhandenen Altbranches wurden bewusst
noch nicht entfernt.

## FPS-Experiment

Die 14 geaenderten, FPS-bezogenen Dateien aus

`C:\Users\marco\OneDrive\Desktop\led_controller_respeaker_0726`

wurden nicht in `main` uebernommen. Sie sind vollstaendig und bytegenau gesichert unter:

`C:\Users\marco\source\recovery\led_controller_respeaker_2026-07-28\fps_experiment`

Die Sicherung enthaelt den Main-Ausgangsstand, die 14 geaenderten Dateien, SHA-256-Pruefsummen
und einen portablen Diff. Der bekannte Cache-Fehler des Experiments ist im dortigen
`README.md` dokumentiert.

## Sicherung der alten Git-Zustaende

Sicherungsort:

`C:\Users\marco\source\recovery\led_controller_respeaker_2026-07-28\git_backups`

Gesichert wurden:

- das aeussere Repository unter `P:\CodexApp\led_controller_respeaker`;
- das darin verschachtelte, eigenstaendige Repository;
- alle vier zugeordneten Codex-Worktrees;
- alle lokalen und Remote-Refs, Tags, der Stash und die Worktree-HEADs;
- alle versionierten lokalen Aenderungen als Binary-Patches;
- alle nicht versionierten Dateien als Pfadlisten und ZIP-Archive.

Beide Git-Bundles wurden mit `git bundle verify` geprueft und enthalten eine
vollstaendige Historie. Die Dirty-Staende hatten zum Sicherungszeitpunkt:

| Bestand | Status-Eintraege | Nicht versionierte Dateien |
|---|---:|---:|
| Aeusseres Repository | 178 | 1 verschachteltes Repository |
| Verschachteltes Repository | 191 | 255 |
| Codex-Worktree `4364` | 249 | 4 |
| Codex-Worktree `c30c` | 1 | 1 |
| Codex-Worktree `f059` | 4 | 3 |
| Codex-Worktree `f964` | 22 | 0 |

## Build- und Cache-Bereinigung

Pytest legt seine temporaeren Daten jetzt gebuendelt unter `tests/.cache` ab:

- `tmp` fuer `tmp_path` und `--basetemp`;
- `pytest_cache` fuer den Pytest-Cache;
- `pycache` fuer Python-Bytecode;
- `effect_build` fuer nur waehrend der Tests benoetigte Effektartefakte.

Nach jeder Testsitzung wird `tests/.cache` automatisch entfernt. Projektbezogene
`__pycache__`-Ordner unter `src`, `tests`, `tools` und `build-tools` werden ebenfalls
entfernt. `.venv` wird von dieser Bereinigung nicht erfasst.

Beim Effekt-Build liegen generierte Quellen, einzelne LEFX-Pakete und Set-Staging jetzt
unter:

`tools\effect_building\build\.cache`

Nach einem erfolgreichen Standard-LEFXSET-Build wird dieser Cache automatisch entfernt.
Die fertigen Artefakte bleiben unter:

- `tools\effect_building\build\output\default-effects.lefxset`
- `tools\effect_building\build\published\default-effects.lefxset`

## Verifikation

Durchgefuehrte Pruefungen:

- Effekt-Build mit `--rebuild-packages`: erfolgreich;
- LEFXSET-Verifikation: 37 Effekte und 148 Commands erfolgreich validiert;
- gezielte Regressionstests: erfolgreich;
- vollstaendige Suite: `119 passed in 161.91s`;
- Service-Smoke mit `--no-device`: `ping`, `status`, 37 Effekte und `shutdown`;
- Service-Ausgabe: `console-preview`, 8 FPS;
- Service-Prozess: sauber mit Exitcode 0 beendet;
- nach dem Testlauf: kein `tests/.cache` und kein Projekt-`__pycache__` vorhanden.

## Nachtraeglich freigegebene Bereinigung

Die unabhaengigen Altprojektpfade und Archive wurden nach einer gesonderten Freigabe
entfernt. Die Codex-Worktrees und ihre zentrale Git-Datenbank unter
`P:\CodexApp\led_controller_respeaker` wurden ausdruecklich behalten, weil die
Worktrees ohne diese Datenbank nicht mehr funktionieren wuerden.

Auf GitHub wurden die drei Altbranches entfernt; dort ist nur noch `main` vorhanden.
Der genaue Endzustand steht in `2026-07-28_entfernungsprotokoll.md`.
