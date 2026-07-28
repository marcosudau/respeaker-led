# Entfernungskandidaten vom 2026-07-28

> **Status nach Freigabe:** Diese Kandidatenliste dokumentiert den Stand vor der
> Ausfuehrung. Die tatsaechlich entfernten und bewusst behaltenen Pfade stehen im
> verbindlichen Abschlussprotokoll `2026-07-28_entfernungsprotokoll.md`.
> Die Codex-Worktrees und ihre zentrale Git-Datenbank auf `P:` wurden auf
> nachtraeglichen Wunsch ausdruecklich nicht entfernt.

## Status und Regel

Diese Liste ist eine Freigabeliste, kein Protokoll bereits erfolgter Loeschungen.
Keiner der hier genannten Altprojekt-Pfade und keiner der GitHub-Altbranches wurde
entfernt.

Die Sicherungen liegen unter:

`C:\Users\marco\source\recovery\led_controller_respeaker_2026-07-28`

## Gruppe A: Zur Entfernung empfohlen

### 1. Alte Codex-Worktrees

Diese vier Arbeitsverzeichnisse gehoeren zur alten Git-Datenbank auf `P:`. Ihre
versionierten und nicht versionierten Aenderungen sind gesichert.

1. `C:\Users\marco\.codex\worktrees\4364\led_controller_respeaker`
2. `C:\Users\marco\.codex\worktrees\c30c\led_controller_respeaker`
3. `C:\Users\marco\.codex\worktrees\f059\led_controller_respeaker`
4. `C:\Users\marco\.codex\worktrees\f964\led_controller_respeaker`

Entfernt werden sollen nur diese vier projektspezifischen Worktree-Verzeichnisse,
nicht `C:\Users\marco\.codex` insgesamt und nicht die dortigen Sessions, Skills,
Plugins oder sonstigen Codex-Daten.

### 2. Altes verschachteltes Git-Konstrukt auf P:

Gesamter vorgesehener Entfernungspfad:

`P:\CodexApp\led_controller_respeaker`

Dieser Pfad enthaelt sowohl die aeussere Git-Datenbank als auch das folgende
eigenstaendige, verschachtelte Repository:

`P:\CodexApp\led_controller_respeaker\led_controller_respeaker_letzer__stand_ordnerversion`

Der Kindpfad ist zur Transparenz einzeln genannt, wird aber bereits durch die Entfernung
des Elternpfads erfasst und darf nicht als zweiter unabhaengiger Loeschschritt behandelt
werden.

### 3. Doppelt entpackter sauberer Download

Gesamter vorgesehener Entfernungspfad:

`C:\Users\marco\Downloads\led_controller_respeaker-main`

Darin enthalten:

- `C:\Users\marco\Downloads\led_controller_respeaker-main\led_controller_respeake`
- `C:\Users\marco\Downloads\led_controller_respeaker-main\led_controller_respeaker-main`

Beide enthaltenen Kopien entsprachen bei der Pruefung exakt dem damaligen GitHub-Main
`213027221392deb1e9683cb8ca201906e16219f3`.

## Gruppe B: GitHub-Branches zur spaeteren Entfernung

Auf GitHub sind aktuell genau diese Altbranches neben `main` vorhanden:

1. `codex/develop-branch` bei `0fae51c3f8c3deefd5d51aec6d81efe73cb81253`
2. `codex/effekt-dateien` bei `5b43937226f9d896905efc22dca781b6f22c11bd`
3. `copilot/create-doa-integration-plan` bei `228d738b41624fe7d2820e7ce0a18cbfb930ea2d`

Zielzustand nach Freigabe: Auf GitHub bleibt nur `main`. Die Historie dieser Branches
ist bereits im verifizierten Bundle `outer_repository_all_refs.bundle` gesichert.

## Gruppe C: Optionale Bereinigung innerhalb des FPS-Experiments

Diese Ziele sind keine unmittelbaren Entfernungsempfehlungen. Sie koennen nach
Durchsicht des Desktop-Experiments separat freigegeben werden:

1. `C:\Users\marco\OneDrive\Desktop\led_controller_respeaker_0726\.pytest_tmp_report_audit`
2. `C:\Users\marco\OneDrive\Desktop\led_controller_respeaker_0726\effects\default-effects.lefxset`
3. `C:\Users\marco\OneDrive\Desktop\led_controller_respeaker_0726\requirements.txt`

Der zweite Pfad ist ein zusaetzliches Release-Artefakt, das im Desktop-Experiment zwei
Tests beeinflusst hat. Der dritte Pfad ist eine leere, nicht versionierte Datei.

## Ausdruecklich behalten

Diese Pfade duerfen bei der bevorstehenden Bereinigung nicht entfernt werden:

1. `C:\Users\marco\source\repos\led_controller_respeaker`
2. `C:\Users\marco\source\recovery\led_controller_respeaker_2026-07-28`
3. `C:\Users\marco\OneDrive\Desktop\led_controller_respeaker_0726`

Der dritte Pfad bleibt als originale FPS-Arbeitskopie erhalten, bis die FPS-Entwicklung
spaeter separat fortgesetzt oder bewusst archiviert wird.

## Vorerst nicht entfernen: ungepruefte Legacy-Bestaende

Diese Verzeichnisse sind aeltere, fachlich abweichende Implementierungen oder
Dokumentationsbestaende. Sie sind nicht Teil der unmittelbaren Git-Bereinigung:

- `C:\Users\marco\OneDrive\Desktop\respeaker_led_controller`
- `C:\Users\marco\OneDrive\Desktop\respeaker_led_controller_frühe_version\respeaker_led_controller`
- `P:\CodexApp\ReSpeaker\respeaker_led_controller`
- `C:\Users\marco\OneDrive\Desktop\OpenClaw\ProjekteClawie\led_control_layer_sst\example_respeaker_led_controller`
- `C:\Users\marco\OneDrive\Desktop\docs_led_controller`
- `C:\Users\marco\OneDrive\Desktop\ToloriaVault\docs_respeaker_led_controller_frühe_version`

Vor einer spaeteren Entfernung waere jeweils eine eigene Inhalts- und
Archivierungsentscheidung erforderlich.

## Reihenfolge nach Freigabe

1. Sicherungsdateien und SHA-256-Pruefsummen noch einmal pruefen.
2. Die vier alten Worktrees kontrolliert aus der alten Git-Datenbank austragen.
3. Die vier projektspezifischen Worktree-Verzeichnisse entfernen.
4. `P:\CodexApp\led_controller_respeaker` entfernen.
5. Den doppelten Downloadordner entfernen.
6. Die drei GitHub-Altbranches entfernen.
7. GitHub und den kanonischen Klon pruefen: nur `main`, sauberer Status, gleicher HEAD.
