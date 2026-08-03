# Empfehlungen nach der Sanierung

Stand: 2026-07-08

## 1. Effekt-Source-Struktur bereinigen

Hoechste fachliche Prioritaet nach der Git-Sanierung.

Problem:

- `tools/effect_building/build/` soll leerbar sein.
- In `tools/effect_building/build/sources/` liegen aber Source-Artefakte bzw. Source-Kopien.
- `tools/effect_building/sorted_by_type/` enthaelt eine begonnene manuelle Sortierung, ist aber noch kein offizieller Pfad.

Empfehlung:

- Neue offizielle Source-Struktur definieren, z. B. unter `tools/effect_building/effect_sources/`.
- Effektarten explizit trennen: `states/`, `overlays/`, `events/`.
- Build-Skripte so anpassen, dass `build/` nur noch Ausgabe enthaelt.
- Danach darf `tools/effect_building/build/` gefahrlos geloescht und neu erzeugt werden.

## 2. Effektarten als Vertrag modellieren

Problem:

- `STATES`, `OVERLAYS` und `EVENTS` unterscheiden sich in Dauer, Layern, Prioritaet und Kompatibilitaet.
- Diese Unterschiede sind noch nicht konsequent genug im Code und in den Paketmetadaten erzwungen.

Empfehlung:

- `effect_kind` oder aehnliches Metadatum in den Effektdefinitionen fest verankern.
- Registry pruefen lassen, ob Effektart und erlaubte Layer zusammenpassen.
- Commands/Preset-Namen nach Effektart strukturieren.
- Tests fuer falsche Layer-Zuordnung ergaenzen.

## 3. DoA-Live-Integration separat umsetzen

Problem:

- DoA-Effekte existieren als Effektbasis.
- Hardware-Lesepfad existiert teilweise als Beispiel.
- Runtime und Service haben aber noch keinen DoA-Snapshot-/Polling-Vertrag.

Empfehlung:

- `ReSpeakerAdapter.read_doa_snapshot()` oder vergleichbaren Adaptervertrag einfuehren.
- Service-seitiges Polling implementieren.
- Runtime-API fuer DoA-Snapshot ergaenzen.
- DoA-Overlay nur ueber normalen Overlay-Mechanismus darstellen, nicht als Sonderpfad im Renderer.

## 4. Optionale `config.json` nachziehen

Problem:

- Planung ist vorhanden.
- Code nutzt weiterhin Temp-Pfade und `background_state.json`.

Empfehlung:

- Kleinen `config_loader` einfuehren.
- `background_state`-Konfiguration mit klarer Prioritaet umsetzen.
- Bestehenden Fallback auf `background_state.json` vorerst erhalten.
- Logging-Optionen erst danach anbinden.

## 5. Build-/Release-Doku aktualisieren

Problem:

- Build- und Release-Pfad ist funktional, aber mehrere Planungsdokumente sind historisch oder teilweise ueberholt.

Empfehlung:

- `build-tools/README.md` und `build-tools/RELEASE.md` als aktuelle Wahrheit behandeln.
- Historische Planungsdokumente nicht loeschen, aber mit Statushinweisen versehen.
- In `docs/reports/` die Sanierungsaktion als Einstiegspunkt fuer spaetere Weiterentwicklung nutzen.

## 6. Worktree-/Branch-Hygiene beibehalten

Empfehlung:

- Dauerhaft nur `main` als Hauptbranch.
- Kurzlebige Arbeitsbranches mit klarer Aufgabe.
- Keine parallelen Langzeit-Worktrees ohne dokumentierten Zweck.
- Vor Branch-Loeschungen immer Backup-Tag oder Backup-Branch behalten.

## 7. Testabdeckung gezielt erweitern

Empfehlung:

- Tests fuer Effektarten und erlaubte Layer.
- Tests fuer Build-Ordner-Cleanup, sobald Source-Migration erledigt ist.
- Tests fuer Paket-/Registry-Konsistenz nach Effektart.
- Service-Smoke fuer `--no-device`, `list-effects`, `apply-effect`, `shutdown`.

