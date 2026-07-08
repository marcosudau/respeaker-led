# Git- und Projekt-Sanierungsplan

Stand: 2026-07-08  
Ziel: Das Projekt wieder auf einen sauberen, weiterentwickelbaren Zwischenstand bringen, idealerweise mit genau einem kuenftig relevanten Arbeitsbranch `main`.

## Zusammenfassung

Der beste technische Stand ist nach aktueller lokaler Analyse `codex/develop-branch`.

Begruendung:

- `main` ist ein Vorfahr von `codex/develop-branch`.
- `codex/effekt-dateien` ist ebenfalls ein Vorfahr von `codex/develop-branch`.
- `codex/develop-branch` enthaelt 9 Commits mehr als `origin/main`.
- `codex/develop-branch` enthaelt 22 Commits mehr als `origin/codex/effekt-dateien`.
- Die Effekt-/Build-Trennung, die aktuelle Doku und der neue Build-Pfad liegen auf `codex/develop-branch`.

Der Plan unten zielt deshalb darauf:

1. den aktuellen Stand zu sichern;
2. staged/untracked/ignored Chaos sauber zu entscheiden;
3. Tests wieder gruen zu bekommen;
4. `main` auf den Stand von `codex/develop-branch` zu bringen;
5. alte Branches/Worktrees nicht sofort hart zu loeschen, sondern erst nach Sicherung aus dem aktiven Arbeitsfluss zu nehmen.

## Wichtige Einschraenkung der Analyse

`git fetch --all --prune` konnte nicht ausgefuehrt werden, weil GitHub-Credentials in dieser Umgebung fehlen:

```text
fatal: could not read Username for 'https://github.com': No such file or directory
```

Die Analyse basiert deshalb auf den lokal vorhandenen Remote-Refs:

- `origin/main`
- `origin/codex/develop-branch`
- `origin/codex/effekt-dateien`
- `origin/copilot/create-doa-integration-plan`

Vor einer finalen Remote-Aktion sollte nach Moeglichkeit einmal mit funktionierender GitHub-Authentifizierung gefetcht werden.

## Aktueller Git-Zustand

Aktiver Branch:

```text
codex/develop-branch...origin/codex/develop-branch
```

Worktrees:

```text
P:/CodexApp/led_controller_respeaker                          main
C:/Users/marco/.codex/worktrees/4364/led_controller_respeaker codex/develop-branch
C:/Users/marco/.codex/worktrees/c30c/led_controller_respeaker detached
C:/Users/marco/.codex/worktrees/f059/led_controller_respeaker detached
C:/Users/marco/.codex/worktrees/f964/led_controller_respeaker detached
```

Dieser Ordner ist ein Worktree. Seine `.git`-Datei zeigt auf:

```text
P:/CodexApp/led_controller_respeaker/.git/worktrees/led_controller_respeaker3
```

Das erklaert einen grossen Teil der Verwirrung: Es gibt nicht nur Branches, sondern mehrere parallele Arbeitsverzeichnisse.

## Branch-Befund

### `main`

`main` steht bei `efe6ebf` und ist ein Vorfahr von `codex/develop-branch`.

Bewertung:

- `main` ist aktuell nicht der beste Arbeitsstand.
- `main` sollte nicht weiterentwickelt werden, bevor es auf `codex/develop-branch` aktualisiert wurde.

### `codex/effekt-dateien`

`codex/effekt-dateien` steht bei `5b43937` und ist ebenfalls ein Vorfahr von `codex/develop-branch`.

Bewertung:

- Der Branch muss nicht gemerged werden; sein Inhalt ist im Develop-Stand enthalten.
- Er kann nach Sicherung spaeter archiviert oder geloescht werden.

### `codex/develop-branch`

`codex/develop-branch` steht bei `0fae51c`.

Bewertung:

- Das ist der Kandidat fuer den neuen kanonischen `main`.
- Dieser Branch enthaelt die aktuell beste Trennung zwischen Hauptlogik und Effekten.

### `origin/copilot/create-doa-integration-plan`

Dieser Branch hat genau einen Commit, der nicht in `codex/develop-branch` steckt:

```text
228d738 DoA Integrationskonzept dokumentieren
```

Bewertung:

- Das ist nach aktuellem Befund nur Planungsdoku, keine Runtime-Implementierung.
- Der Inhalt scheint lokal bereits als untracked Planungsdatei `docs/planning/11_konzept_DoA_integration_und_template.md` vorhanden zu sein.
- Nicht als Code-Branch behandeln; hoechstens Doku gezielt uebernehmen.

## Aktueller Working-Tree-Befund

### Staged Aenderungen

Aktuell staged:

- `.gitignore`
- `build-tools/scripts/create_release_bundle.py`
- `src/__init__.py`
- `tests/build_artifact_helpers.py`

Bewertung:

- `.gitignore`: sinnvoll; ignoriert Kate-Swap-Dateien und `tools/effect_building/sorted_by_type/`.
- `src/__init__.py`: wahrscheinlich sinnvoll; macht Versionsauflosung robuster, falls `build-tools/version.py` in Paket-/Installationskontexten nicht vorhanden ist.
- `tests/build_artifact_helpers.py`: wahrscheinlich sinnvoll, aber pruefen; Tests ignorieren fehlende/ungueltige Builtin-Discovery-Eintraege nun toleranter.
- `build-tools/scripts/create_release_bundle.py`: fachlich plausibel, aber aktuell nicht testkonsistent. Der Code verlangt jetzt `force=True`, wenn vorhandene ZIPs/Staging-Ordner ueberschrieben werden sollen.

### Aktueller Teststatus

Ausgefuehrt:

```text
uv run pytest -q --basetemp=.pytest_tmp
```

Ergebnis:

```text
115 passed, 1 failed
```

Fehlschlag:

```text
tests/test_release_tooling.py::test_create_release_bundle_replaces_existing_zip_without_force
```

Ursache:

- Test erwartet altes Verhalten: vorhandenes ZIP wird ohne `force` ersetzt.
- Staged Code implementiert neues Verhalten: vorhandenes ZIP ohne `force` ist ein Fehler.

Empfehlung:

- Neues Verhalten behalten.
- Test anpassen: Ohne `force` muss `FileExistsError` kommen; mit `force=True` muss Ueberschreiben funktionieren.

Grund:

- Schutz vor versehentlichem Ueberschreiben ist fuer Release-Bundles sinnvoll.
- `--force` existiert bereits und ist im Build-Ablauf auch der erwartbare explizite Ueberschreibmodus.

### Untracked Dateien

Aktuell untracked:

- `docs/planning/10_konzept_config_json_und_release_runtime_pfade.md`
- `docs/planning/11_konzept_DoA_integration_und_template.md`
- `docs/planning/Effekte_Konzepte/`
- `docs/reports/`

Bewertung:

- `docs/reports/` enthaelt die neu erstellten Analyseberichte und diesen Plan. Diese Dateien sollten bewusst committed werden.
- Die untracked Planungsdokumente wirken wie relevante lokale Doku aus spaeteren Planungsphasen. Sie sollten nicht blind geloescht werden.
- `10_konzept_config_json_und_release_runtime_pfade.md` enthaelt den relevanten Entscheidungsnachtrag zur Beibehaltung von `background_state.json` als Zwischen-Fallback.
- `12_integrationskonzept_fuer_optionale_config.md` wurde als nahezu identische Dublette erkannt und endete mit einem fremden Worktree-Pfad. Sie wird deshalb nicht in den bereinigten Stand uebernommen.
- `11_konzept_DoA_integration_und_template.md` deckt sich mit dem separaten Copilot-Branch-Inhalt und sollte als Doku uebernommen werden, falls der Planungsstand erhalten bleiben soll.

### Ignored Arbeitsreste

Relevante ignored Pfade:

- `.pytest_tmp/`
- `.venv/`
- `dist/`
- `logs/`
- `tools/effect_building/build/`
- `tools/effect_building/sorted_by_type/`
- diverse `__pycache__/`

`tools/effect_building/sorted_by_type/` enthaelt aktuell viele manuell sortierte Effektdateien. Darin liegen unter anderem Varianten eines `doa_activity_indicator`, aber dieser Ordner ist nicht Teil des offiziellen Buildpfads.

Wichtige Korrektur: `tools/effect_building/build/` darf im Zielbild nur erzeugte Build-/Zwischen-/Runtime-Dateien enthalten und muss deshalb grundsaetzlich komplett leerbar sein. Aktuell existiert darin aber ein Unterordner `sources/` mit Effekt-Source-Artefakten bzw. Source-Kopien. Das ist eine kritische Inkonsistenz: Effektquellen duerfen nicht in einem Cleanup-Ziel liegen.

Bewertung:

- `sorted_by_type/` ist ein begonnener manueller Sortierstand fuer die spaetere Trennung nach Effektarten.
- Er darf nicht als aktueller offizieller Buildpfad missverstanden werden.
- Er darf aber auch nicht pauschal geloescht werden, bevor geklaert ist, welche Inhalte daraus in eine neue Source-Struktur uebernommen werden sollen.
- Fuer diesen Git-Zwischenstand bleibt `sorted_by_type/` ignoriert. Die fachliche Migration wird als eigener Folgepunkt dokumentiert.

## Halb oder nur teilweise umgesetzte Themen

### 1. `config.json` / optionale Startkonfiguration

Planungsstand vorhanden:

- `docs/planning/10_konzept_config_json_und_release_runtime_pfade.md`

Code-Ist-Zustand:

- Es gibt noch keinen `config_loader.py`.
- `src/infrastructure/paths.py` definiert keine `CONFIG_FILE`.
- `ControllerService` nutzt weiterhin `background_state_store.py`.
- `background_state.json` wird weiterhin gelesen und geschrieben.
- Logging-Gates ueber config sind nicht implementiert.

Bewertung:

- Nicht als unfertiger Codebruch, sondern als geplantes, noch nicht umgesetztes Feature behandeln.
- Nicht in die Git-Sanierung ziehen.

### 2. DoA-Live-Integration

Planungsstand vorhanden:

- `docs/planning/11_konzept_DoA_integration_und_template.md`
- `docs/planning/Effekte_Konzepte/DoA_Konzept_Integration_und_Template.md`

Code-Ist-Zustand:

- `src/python_control/xvf_host.py` kennt `AUDIO_MGR_SELECTED_AZIMUTHS` und `DOA_VALUE`.
- `src/python_control/respeaker_get_doa.py` ist als Beispiel/Tool vorhanden.
- `ReSpeakerAdapter` hat noch keine lesende DoA-Methode.
- `ControllerService` hat noch kein DoA-Polling.
- `ControllerRuntime` hat nur `set_direction(float)`, aber kein `set_doa_snapshot(...)`.
- Standard-Effekte enthalten `doa_direction_dot` und `doa_direction_segment`, aber kein aktives Live-DoA-Polling.
- In `tools/effect_building/sorted_by_type/` gibt es experimentelle DoA-Artefakte, die nicht offizieller Buildpfad sind.

Bewertung:

- Effektseitige DoA-Basis ist teilweise vorhanden.
- Live-Hardwareintegration ist nicht umgesetzt.
- Dieses Thema sollte als spaeteres Feature separat geplant werden.

### 3. Release-Tooling

Code-Ist-Zustand:

- Build- und Release-Tooling existiert unter `build-tools/`.
- Der Build kann Effektartefakte bauen, EXE bauen, Bundle erzeugen und pruefen.
- Staged Aenderung fuehrt `force`-Schutz fuer vorhandene Release-Bundles ein.

Problem:

- Test ist nicht an das neue Verhalten angepasst.

Bewertung:

- Akuter Sanierungspunkt, weil die Tests rot sind.
- Muss vor der Main-Konsolidierung geloest werden.

### 4. Build-/Scratch-Artefakte im Repo-Kontext

Code-/Datei-Ist-Zustand:

- Offizielle Build-Artefakte liegen unter `tools/effect_building/build/` und sind ignored.
- `build_config.json` verweist auf diese Artefakte.
- `sorted_by_type/` ist ignored und nicht offizieller Buildpfad.
- Alte Artefakte wie PySide6-Testapp-EXE und Runtime-Caches wurden auf Develop im Vergleich zu Main bereinigt.
- Kritische Inkonsistenz: Unter `tools/effect_building/build/sources/` liegen Source-Artefakte bzw. Source-Kopien. Ein Ordner namens `build` muss aber komplett leerbar sein.

Bewertung:

- Kein akuter Runtime-Codebruch.
- Aber hoher Architektur- und Cleanup-Risikofaktor.
- Vor einem aggressiven Cleanup von `tools/effect_building/build/` muessen die Source-Artefakte aus `build/sources/` in eine echte Source-Struktur migriert werden.
- Die begonnene manuelle Sortierung unter `tools/effect_building/sorted_by_type/` ist dafuer relevanter Kontext.

### 5. Effektarten sind fachlich noch nicht hart genug getrennt

Fachlicher Soll-Zustand:

- `STATES`: dauerhaft oder unbestimmt laufende Grundmodi fuer die unteren State-Layer.
- `OVERLAYS`: Funktionsanzeigen auf Overlay-Layern, z. B. DoA, Progressring, Timer oder Lautstaerke.
- `EVENTS`: kurze einmalige Signale mit fester Dauer und hoechster kurzfristiger Prioritaet.

Bewertung:

- Diese Effektarten haben unterschiedliche Laufzeitregeln, Layer-Zuordnung, Dauersemantik und Kompatibilitaet.
- Die Trennung ist konzeptionell angelegt, aber im Dateisystem und in den Source-/Build-Pfaden noch nicht sauber genug ausgedrueckt.
- Das ist ein Folgepunkt nach der Git-Sanierung, nicht Teil des reinen Main-Fast-Forwards.

## Zielbild nach der Sanierung

Nach Umsetzung des Plans sollte gelten:

- `main` zeigt auf denselben Commit wie der bereinigte `codex/develop-branch`.
- Es gibt keine staged/untracked Dateien ohne bewusste Entscheidung.
- `uv run pytest -q --basetemp=.pytest_tmp` ist gruen.
- Effektset-Verifikation ist gruen.
- Die neu erstellten Reports und der Sanierungsplan sind versioniert.
- Alte Branches bleiben entweder als remote Archiv erhalten oder werden nach Sicherung geloescht.
- Neue Arbeit findet nur noch auf `main` oder kurzlebigen `codex/...` Arbeitsbranches statt.

## Konkreter Umsetzungsplan

### Phase 0: Sicherheitsnetz vor jeder Bereinigung

Ziel: Nichts verlieren, bevor Branches oder Worktrees angefasst werden.

Schritte:

1. Lokalen Zustand dokumentieren:

   ```powershell
   git status --short --branch
   git branch -vv --all
   git worktree list
   git log --oneline --decorate --graph --all -n 40
   ```

2. Backup-Branch fuer aktuellen Develop-Stand anlegen:

   ```powershell
   git branch codex/backup-before-main-cleanup codex/develop-branch
   ```

3. Optional zusaetzlich Tag setzen:

   ```powershell
   git tag backup-before-main-cleanup-2026-07-08 codex/develop-branch
   ```

4. Keine Branches loeschen, bevor der neue `main` gruen ist.

Entscheidung erforderlich:

- Soll ein lokaler Backup-Branch reichen, oder soll zusaetzlich ein Tag gesetzt werden?

Empfehlung:

- Beides setzen. Das ist billig und reversibel.

### Phase 1: Staged Aenderungen sauber machen

Ziel: Die bereits staged Aenderungen entweder korrekt integrieren oder bewusst verwerfen. Empfehlung: integrieren.

Schritte:

1. `build-tools/scripts/create_release_bundle.py` behalten:
   - `force=False` blockiert vorhandene ZIPs/Staging-Ordner.
   - `force=True` erlaubt Ueberschreiben.

2. `tests/test_release_tooling.py` anpassen:
   - bestehenden Test `test_create_release_bundle_replaces_existing_zip_without_force` ersetzen oder umbenennen in `test_create_release_bundle_requires_force_for_existing_zip`.
   - neuen Test ergaenzen: `test_create_release_bundle_replaces_existing_zip_with_force`.

3. `.gitignore`-Aenderungen behalten:
   - `*.kate-swp`
   - `tools/effect_building/sorted_by_type/`

4. `src/__init__.py`-Aenderung behalten:
   - Version zuerst aus `build-tools/version.py`, sonst aus Paketmetadaten, sonst `0+unknown`.

5. `tests/build_artifact_helpers.py` pruefen und behalten, wenn die Toleranz zu `build_config.json` dem Runtime-Verhalten entspricht.

Validierung:

```powershell
uv run pytest tests/test_release_tooling.py -q --basetemp=.pytest_tmp
uv run pytest -q --basetemp=.pytest_tmp
```

Erwartung:

- Release-Tooling-Tests gruen.
- Gesamtsuite gruen.

### Phase 2: Untracked Doku entscheiden

Ziel: Keine wertvollen Planungsdateien verlieren, aber keine Dubletten unbesehen in `main` ziehen.

Schritte:

1. `docs/reports/` committen:
   - `hauptlogik_analyse_2026-07-08.md`
   - `effekte_analyse_2026-07-08.md`
   - `git_sanierungsplan_2026-07-08.md`

2. `docs/planning/11_konzept_DoA_integration_und_template.md` committen oder mit dem Copilot-Branch-Dokument abgleichen:
   - Empfehlung: committen, weil es den einzigen nicht integrierten Copilot-Branch-Inhalt abdeckt.

3. `docs/planning/10_konzept_config_json_und_release_runtime_pfade.md` committen:
   - Empfehlung: committen, weil diese Datei den relevanten Entscheidungsnachtrag zur `background_state.json`-Zwischenloesung enthaelt.
   - Die zuvor untracked Datei `12_integrationskonzept_fuer_optionale_config.md` nicht uebernehmen, weil sie eine nahezu identische Dublette ohne Mehrwert war.

4. `docs/planning/Effekte_Konzepte/` pruefen:
   - Wenn es Konzept-/Brainstorming-Charakter hat: entweder committen als Planungskontext oder nach `docs/history_and_legacy/` verschieben.
   - Nicht mit aktivem Code verwechseln.

Entscheidung erforderlich:

- Sollen die untracked Planungsdokumente Teil des bereinigten `main` werden?

Empfehlung:

- `10`, `11` und `Effekte_Konzepte/` behalten.
- `12` nicht uebernehmen, weil es keinen eigenen Mehrwert gegenueber `10` hatte.

### Phase 3: Ignored Arbeitsreste bereinigen

Ziel: Der Arbeitsbaum soll fuer dich visuell verstaendlich sein.

Nicht committen:

- `.pytest_tmp/`
- `.venv/`
- `dist/`
- `logs/`
- `__pycache__/`
- erzeugte Inhalte unter `tools/effect_building/build/`
- `tools/effect_building/sorted_by_type/` als aktueller offizieller Buildpfad

Empfohlene lokale Bereinigung nach erfolgreicher Validierung:

```powershell
Remove-Item -Recurse -Force .pytest_tmp
Remove-Item -Recurse -Force dist
Remove-Item -Recurse -Force logs
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
```

Wichtig:

- `.venv/` nicht loeschen, wenn die lokale Entwicklungsumgebung erhalten bleiben soll.
- `tools/effect_building/build/` nicht pauschal loeschen, solange `build/sources/` noch Source-Artefakte enthaelt.
- `tools/effect_building/sorted_by_type/` nicht loeschen, solange die manuelle Sortierung noch als Vorlage fuer die Effektarten-Migration gebraucht wird.
- Erst nach einer eigenen Effekt-Source-Migration darf `build/` wirklich als komplett leerbarer Build-Ordner behandelt werden.

Entscheidung:

- `tools/effect_building/build/` bleibt vorerst lokal erhalten.
- `tools/effect_building/sorted_by_type/` bleibt vorerst lokal erhalten und ignored.
- Die Bereinigung/Migration der Effektquellen wird als Folgepunkt in den Empfehlungen dokumentiert.

### Phase 4: Funktionalen Zwischenstand herstellen

Ziel: Bevor Branches bewegt werden, muss der Stand fachlich gruen sein.

Pflichtvalidierung:

```powershell
uv run python tools\effect_packager.py verify-effect-package tools\effect_building\build\build_lefxset\default-effects.lefxset
uv run python -c "from src.engine.effect_registry import build_default_effect_registry; r=build_default_effect_registry(); print(len(r.list_effect_ids()), len(r.list_effect_presets()), len(r.list_effect_commands()))"
uv run pytest -q --basetemp=.pytest_tmp
```

Erwartung:

- Effektset-Verifikation erfolgreich.
- Registry zeigt 37 Effekte, 148 Presets, 148 Commands.
- Tests komplett gruen.

Optionaler Service-Smoke:

```powershell
python .\main.py --no-device serve --host 127.0.0.1 --port 8765 --port-pool 8765-8770
python .\main.py ping
python .\main.py list-effects
python .\main.py apply-effect solid_color main --params '{"color":"0x224466"}'
python .\main.py shutdown
```

Hinweis:

- Der Service-Smoke braucht wegen laufendem Server ein separates Terminal oder einen kontrollierten Hintergrundprozess. Die Test-Suite deckt schon viel ab; fuer "sauberer Zwischenstand" ist der Smoke aber sinnvoll.

### Phase 5: Einen sauberen Commit auf `codex/develop-branch` erstellen

Ziel: Alle akzeptierten Korrekturen und Reports in einem nachvollziehbaren Commit sichern.

Empfohlener Commit-Inhalt:

- Testfix fuer Release-Tooling.
- Bereits staged Verbesserungen, soweit bestaetigt.
- Neue Reports unter `docs/reports/`.
- Ausgewaehlte Planungsdoku, falls entschieden.
- Keine ignored Build-/Cache-Artefakte.
- Keine experimentellen `sorted_by_type/`-Dateien.

Beispiel:

```powershell
git status --short
git add .gitignore build-tools/scripts/create_release_bundle.py src/__init__.py tests/build_artifact_helpers.py tests/test_release_tooling.py docs/reports
git add docs/planning/10_konzept_config_json_und_release_runtime_pfade.md docs/planning/11_konzept_DoA_integration_und_template.md
git commit -m "Stabilize project baseline and document cleanup plan"
```

Wenn weitere Planungsdoku bewusst behalten werden soll:

```powershell
git add docs/planning/Effekte_Konzepte
```

`docs/planning/Effekte_Konzepte/` nach Entscheidung adden.

### Phase 6: `main` auf den bereinigten Develop-Stand bringen

Ziel: Danach gibt es wieder einen Hauptbranch, der der beste Stand ist.

Voraussetzung:

- Tests gruen.
- Commit auf `codex/develop-branch` erstellt.
- Backup-Branch/Tag existiert.

Da `origin/main` ein Vorfahr von `codex/develop-branch` ist, ist technisch ein Fast-Forward moeglich.

Lokale Schritte:

```powershell
git switch main
git merge --ff-only codex/develop-branch
```

Falls `main` wegen Worktree-Sperre nicht in diesem Verzeichnis ausgecheckt werden kann:

- `main` ist aktuell im Worktree `P:/CodexApp/led_controller_respeaker` ausgecheckt.
- Dann dort den Fast-Forward ausfuehren:

```powershell
cd P:\CodexApp\led_controller_respeaker
git merge --ff-only codex/develop-branch
```

Validierung danach:

```powershell
git status --short --branch
uv run pytest -q --basetemp=.pytest_tmp
```

Remote-Push erst danach:

```powershell
git push origin main
```

Wichtig:

- Kein `git reset --hard`.
- Kein Force-Push, solange nicht zwingend noetig.
- Da Fast-Forward moeglich ist, sollte kein Rewrite noetig sein.

### Phase 7: Alte Branches und Worktrees aufraeumen

Ziel: Git-Verwirrung reduzieren, ohne Historie zu verlieren.

Erst nach erfolgreichem `main`-Push:

1. `codex/develop-branch` noch eine Weile behalten, bis du sicher bist, dass `main` korrekt ist.
2. `codex/effekt-dateien` als erledigt markieren oder spaeter loeschen, weil der Stand enthalten ist.
3. Detached Worktrees entfernen, falls sie nicht mehr gebraucht werden.

Pruefen:

```powershell
git worktree list
```

Spaeter, wenn sicher:

```powershell
git worktree remove C:\Users\marco\.codex\worktrees\c30c\led_controller_respeaker
git worktree remove C:\Users\marco\.codex\worktrees\f059\led_controller_respeaker
git worktree remove C:\Users\marco\.codex\worktrees\f964\led_controller_respeaker
```

Branch-Loeschung erst nach expliziter Freigabe:

```powershell
git branch -d codex/effekt-dateien
git push origin --delete codex/effekt-dateien
```

`codex/develop-branch` erst loeschen, wenn einige Zeit nur auf `main` gearbeitet wurde.

## Empfohlene Reihenfolge fuer die konkrete Umsetzung durch Codex

Wenn du gruenes Licht gibst, wuerde ich so vorgehen:

1. Backup-Branch und Backup-Tag erstellen.
2. Test fuer `create_release_bundle` an staged Force-Verhalten anpassen.
3. Release-Tooling-Tests laufen lassen.
4. Gesamtsuite laufen lassen.
5. Untracked Doku-Entscheidung mit dir final klaeren.
6. Akzeptierte Doku adden.
7. Einen sauberen Commit auf `codex/develop-branch` erstellen.
8. `main` per Fast-Forward auf diesen Commit bringen.
9. Tests auf `main` nochmals laufen lassen.
10. Push von `main`, falls GitHub-Credentials verfuegbar sind.
11. Alte Worktrees/Branches erst nach separater Freigabe aufraeumen.

## Offene Entscheidungen fuer dich

### Entscheidung 1: Release-Bundle Force-Verhalten

Empfehlung:

- Neues Verhalten behalten: vorhandene ZIPs/Staging-Ordner duerfen nur mit `--force` ueberschrieben werden.
- Tests entsprechend aktualisieren.

Alternative:

- Staged Code zurueck auf altes Verhalten.

### Entscheidung 2: Planungsdoku

Empfehlung:

- `docs/planning/11_konzept_DoA_integration_und_template.md` behalten.
- `docs/planning/10_konzept_config_json_und_release_runtime_pfade.md` behalten.
- `docs/planning/Effekte_Konzepte/` behalten, wenn du den Brainstorming-Kontext im Repo haben willst.
- `docs/planning/12_integrationskonzept_fuer_optionale_config.md` nicht uebernehmen, weil es eine Dublette ohne eigenen Mehrwert war.

### Entscheidung 3: Main-Strategie

Empfehlung:

- `codex/develop-branch` wird nach Gruenstand per Fast-Forward zu `main`.
- Danach wird nur noch `main` als dauerhafter Hauptbranch benutzt.

### Entscheidung 4: Alte Worktrees

Empfehlung:

- Nicht sofort loeschen.
- Erst nach erfolgreichem `main`-Push und kurzer Kontrolle entfernen.

## Nicht in diese Sanierung aufnehmen

Diese Themen sind wichtig, aber nicht Teil des Git-Cleanup-Ziels:

- `config.json` implementieren.
- DoA-Live-Polling implementieren.
- Windows-Dienst bauen.
- Effektmodell weiter umbauen.
- UI/GUI fuer Effektparameter bauen.
- Signaturpruefung fuer Effektpakete einfuehren.

Diese Themen sollten erst nach einem sauberen `main` separat geplant und umgesetzt werden.

## Definition von "sauberer Zwischenstand"

Der Zwischenstand gilt als sauber, wenn alle Punkte erfuellt sind:

- `main` enthaelt den aktuellen Develop-Stand.
- `git status --short` ist leer oder enthaelt nur bewusst ignorierte lokale Dateien.
- Keine staged Aenderungen bleiben offen.
- Keine untracked Doku bleibt unentschieden.
- `uv run pytest -q --basetemp=.pytest_tmp` ist gruen.
- `default-effects.lefxset` laesst sich verifizieren.
- Die wichtigsten Analyse-/Sanierungsreports sind im Repo.
- Alte Branches sind nicht mehr noetig fuer die Weiterentwicklung.
