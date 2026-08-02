# Architektur, Ausrichtung und Entscheidungen

Stand: 2026-07-08

## Grundausrichtung

Das Projekt soll als sauber trennbarer LED-Controller weitergefuehrt werden:

- Hauptlogik, Service, CLI/API und Hardwarezugriff bleiben im `src/`-Bereich.
- Effektdefinitionen werden als eigene Artefakte betrachtet.
- Standard-Effekte werden gebaut und als LEFX-/LEFXSET-Pakete bereitgestellt.
- Die Runtime konsumiert Effektpakete und arbeitet nicht mehr mit hartkodierten Effekt-Implementierungen als primaerer Wahrheit.

## Git-Entscheidung

`codex/develop-branch` ist der Zielstand fuer die Konsolidierung.

Entscheidung:

- `main` wird per Fast-Forward auf den bereinigten Stand von `codex/develop-branch` gebracht.
- Danach ist `main` der dauerhafte Hauptbranch.
- Alte Branches und Worktrees werden nicht sofort geloescht, sondern erst nach Sicherung und erfolgreicher Validierung entfernt.

## Effektmodell

Die Effektarten muessen kuenftig explizit unterschieden werden:

- `STATES`: dauerhaft laufende Grundmodi, nur auf unteren State-Layern.
- `OVERLAYS`: funktionale Ueberlagerungen, z. B. DoA, Timer, Progress, Lautstaerke.
- `EVENTS`: kurze einmalige Signale mit fester Dauer und hoher kurzfristiger Prioritaet.

Entscheidung:

- Diese Typen sollen nicht nur in Namen oder Ordnern sichtbar sein, sondern als fachlicher Vertrag in Source-Struktur, Metadaten, Build, Registry und Layer-Zuordnung auftauchen.
- Die aktuell manuell begonnene Sortierung unter `tools/effect_building/sorted_by_type/` bleibt als Vorlage erhalten, wird aber nicht zum offiziellen Buildpfad erklaert.

## Build-Ordner-Regel

Entscheidung:

- `tools/effect_building/build/` ist im Zielbild ein reiner Build-/Zwischenstandsordner.
- Dieser Ordner muss prinzipiell komplett loeschbar sein.
- Source-Artefakte duerfen dort nicht dauerhaft liegen.

Konsequenz:

- `tools/effect_building/build/sources/` ist ein zu korrigierender Architekturkonflikt.
- Vor einem Cleanup muss geklaert und migriert werden, welche Dateien daraus echte Quellen sind.

## Release-Verhalten

Entscheidung:

- Vorhandene Release-ZIPs oder Staging-Ordner werden ohne `force` nicht ueberschrieben.
- Bewusstes Ueberschreiben erfolgt nur mit `force=True` bzw. `--force`.

Begruendung:

- Release-Artefakte sollten nicht versehentlich ersetzt werden.
- Das Verhalten ist expliziter und besser automatisierbar.

## Doku-Entscheidung

Entscheidung:

- `docs/reports/` dokumentiert die Sanierungsaktion und den analysierten Zwischenstand.
- Dateien in `docs/reports/` beginnen mit Datum im Format `YYYY-MM-DD_...`, damit sie sortierbar bleiben.
- Planungsdokumente duerfen im Repo bleiben, muessen aber als Planung oder Historie erkennbar sein.

## Nicht jetzt entschieden

Diese Themen sind bewusst Folgeentscheidungen:

- Finale `config.json`-Integration.
- DoA-Live-Polling und DoA-Snapshot-Modell.
- Neue offizielle Source-Struktur fuer Effektarten.
- Automatische Regeneration der Standard-Effektpakete beim Dev-Start.
- Signatur-/Integritaetspruefung fuer externe Effektpakete.

