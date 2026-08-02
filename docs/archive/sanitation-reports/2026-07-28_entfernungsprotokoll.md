# Entfernungsprotokoll vom 2026-07-28

## Ergebnis

Die freigegebene Bereinigung ist abgeschlossen. Der neue Hauptstand und seine
Recovery-Ablage blieben unangetastet. Die Codex-Worktrees wurden auf ausdruecklichen
Wunsch ebenfalls behalten.

GitHub enthaelt nur noch:

- `main`

## Geschuetzte und weiterhin vorhandene Pfade

### Neuer Hauptstand und Sicherung

- `C:\Users\marco\source\repos\led_controller_respeaker`
- `C:\Users\marco\source\recovery\led_controller_respeaker_2026-07-28`

### Codex-Worktrees und erforderliche Git-Datenbank

- `P:\CodexApp\led_controller_respeaker`
- `C:\Users\marco\.codex\worktrees\4364\led_controller_respeaker`
- `C:\Users\marco\.codex\worktrees\c30c\led_controller_respeaker`
- `C:\Users\marco\.codex\worktrees\f059\led_controller_respeaker`
- `C:\Users\marco\.codex\worktrees\f964\led_controller_respeaker`

Die vier `.git`-Verweise der Codex-Worktrees zeigen direkt auf
`P:\CodexApp\led_controller_respeaker\.git\worktrees`. Deshalb muss der P:-Pfad
zusammen mit den Worktrees erhalten bleiben. Nach der Bereinigung wurden alle fuenf
Arbeitsverzeichnisse mit `git rev-parse` und `git status` erfolgreich geprueft.

## Durch Codex entfernte Verzeichnisse

- `C:\Users\marco\Downloads\led_controller_respeaker-main`
- `P:\CodexApp\led_controller_respeaker\led_controller_respeaker_letzer__stand_ordnerversion`
- `P:\CodexApp\ReSpeaker\respeaker_led_controller`
- `C:\Users\marco\OneDrive\Desktop\OpenClaw\ProjekteClawie\led_control_layer_sst\example_respeaker_led_controller`
- `C:\Users\marco\OneDrive\Desktop\ToloriaVault\docs_respeaker_led_controller_frühe_version`

Das verschachtelte Repository auf `P:` war eine eigenstaendige Git-Kopie und nicht
die Git-Datenbank der Codex-Worktrees. Seine Historie, Dirty-Aenderungen und
nicht versionierten Dateien sind weiterhin in der Recovery-Ablage gesichert.

## Durch Codex entfernte Archive

- `C:\Users\marco\Downloads\led_controller_respeaker-0.1.2.zip`
- `C:\Users\marco\Downloads\led_controller_respeaker-main.zip`
- `C:\Users\marco\Downloads\led_controller_service_release_bundle.zip`
- `C:\Users\marco\Downloads\led_controller_service_windows_x64.zip`
- `P:\CodexApp\2026-04-12_20-37_led_controller_respeaker.zip`
- `P:\CodexApp\ReSpeaker\respeaker_led_controller.zip`

## Bereits vor dem Codex-Lauf entfernt vorgefunden

Diese Pfade waren bei der Ausfuehrung bereits nicht mehr vorhanden:

- `C:\Users\marco\OneDrive\Desktop\led_controller_respeaker_0726`
- `C:\Users\marco\OneDrive\Desktop\respeaker_led_controller`
- `C:\Users\marco\OneDrive\Desktop\respeaker_led_controller_frühe_version\respeaker_led_controller`
- `C:\Users\marco\OneDrive\Desktop\docs_led_controller`
- `C:\Users\marco\OneDrive\Desktop\led_controller_respeaker_2026-04-19_16-23.zip`

Die FPS-Aenderungen aus der entfernten Desktop-Kopie bleiben in
`C:\Users\marco\source\recovery\led_controller_respeaker_2026-07-28\fps_experiment`
erhalten.

## Entfernte GitHub-Branches

- `codex/develop-branch`
- `codex/effekt-dateien`
- `copilot/create-doa-integration-plan`

Eine anschliessende Abfrage aller Remote-Heads lieferte ausschliesslich `refs/heads/main`.

## Bewusst nicht Teil der Bereinigung

Nicht entfernt wurden Deployment- und Integrationsdateien in anderen aktiven
Projekten, Codex-Sessions, Skills, Plugins, sonstige `.codex`-Metadaten und die
installierte Python-Paketspur. Diese Bestaende sind keine unabhaengigen
Arbeitskopien des neuen Hauptrepositories.

## Nachweis

Das exakt verwendete Cleanup-Skript mit fester Positiv- und Schutzliste liegt unter:

`C:\Users\marco\source\recovery\led_controller_respeaker_2026-07-28\cleanup_approved_2026_07_28.py`
