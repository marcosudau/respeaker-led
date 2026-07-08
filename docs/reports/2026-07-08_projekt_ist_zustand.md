# Projekt-Ist-Zustand

Stand: 2026-07-08

## Zweck des Projekts

Das Projekt ist ein LED-Controller fuer ReSpeaker-/XMOS-basierte LED-Ringe. Es stellt eine lokale Steuerlogik bereit, die Effekte auf mehreren Layern rendert, ueber CLI/API bedient werden kann und fuer spaetere Integration in Host-Anwendungen oder Dienste vorbereitet ist.

## Hauptbestandteile

### Runtime und Rendering

- `src/engine/runtime.py`: verwaltet aktive Layer, Presets, Commands und Rendering-Ausgaben.
- `src/engine/renderer.py`: erzeugt Frames aus Effektdefinitionen und Parametern.
- `src/engine/composer.py`: kombiniert mehrere Layer zu einem finalen LED-Zustand.
- `src/core/layers.py`: definiert Layer- und Prioritaetsmodell.
- `src/core/effect_schema.py` und `src/core/models.py`: zentrale Datenmodelle.

Die Runtime arbeitet layerbasiert. Untere Layer sind fuer Grundzustaende gedacht, obere Layer fuer kurzzeitige oder funktionale Ueberlagerungen.

### Schnittstellen

- `main.py` und `src/__main__.py`: Programmeinstieg.
- `src/interfaces/cli.py`: CLI-Kommandos fuer Start, Ping, Effektlisten, Effektanwendung und Service-Steuerung.
- `src/interfaces/api.py`: HTTP/API-Oberflaeche.
- `src/interfaces/client.py`: Client-Helfer fuer lokale Service-Kommunikation.
- `src/services/service.py` und `src/services/service_hosting.py`: Service-Lebenszyklus, Hosting und Port-Verwaltung.

### Hardware- und Integrationsschicht

- `src/integrations/adapters.py`: Adapter-Abstraktion fuer echte Hardware oder No-Device-Betrieb.
- `src/python_control/xvf_host.py`: Low-Level ReSpeaker/XMOS-Kommandos.
- `src/python_control/respeaker_get_doa.py`: vorhandenes DoA-Beispiel/Tool.

Live-DoA ist vorbereitet, aber noch nicht in Runtime und Service integriert.

### Effekt- und Paketlogik

- `src/engine/effect_package_schema.py`: LEFX-/LEFXSET-Schema.
- `src/engine/effect_package_loader.py`: Laden und Validieren von Effektpaketen.
- `src/engine/effect_package_builder.py`: Erzeugen von Effektpaketen.
- `src/engine/effect_registry.py`: Aufbau der Default-Registry.
- `src/engine/effect_preset_registry.py` und `src/engine/effect_command_registry.py`: Preset- und Command-Zugriff.
- `tools/effect_packager.py`: CLI fuer Effektpaket-Operationen.
- `tools/effect_building/`: Build-Pfad fuer Standard-Effekte.

Aktueller validierter Stand: 37 Effekte, 148 Presets, 148 Commands.

### Build und Release

- `build-tools/build.py`: zentraler Build-Orchestrator.
- `build-tools/build_config.json`: Artefakt- und Discovery-Konfiguration.
- `build-tools/scripts/create_release_bundle.py`: Release-Bundle-Erzeugung.
- `build-tools/scripts/check_release_bundle.py`: Bundle-Pruefung.
- `build-tools/scripts/cleanup_after_build.py`: Cleanup-Helfer.
- `build-tools/template_release_bundle/`: Auslieferungsstruktur.

Der Release-Pfad ist vorhanden und testbar. Die aktuelle Sanierung korrigiert das Verhalten beim Ueberschreiben vorhandener Bundles: ohne `force` wird blockiert, mit `force=True` wird bewusst ueberschrieben.

## Git-Ist-Zustand vor der Sanierung

- `codex/develop-branch` ist der weiteste lokale Stand.
- `main` ist ein Vorfahr von `codex/develop-branch`.
- `codex/effekt-dateien` ist ebenfalls ein Vorfahr von `codex/develop-branch`.
- Es existieren mehrere Worktrees, was die Verwirrung stark erhoeht hat.
- Der Copilot-DoA-Branch enthaelt nach aktuellem Stand nur Doku, keine Runtime-Implementierung.

## Aktuelle offene Baustellen

- Effekt-Source-Dateien liegen teilweise bzw. als Source-Artefakte unter `tools/effect_building/build/sources/`; das widerspricht dem Ziel, `build/` komplett leerbar zu halten.
- `tools/effect_building/sorted_by_type/` enthaelt eine begonnene manuelle Sortierung nach Effektarten, ist aber noch kein offizieller Source-Pfad.
- Die Effektarten `STATES`, `OVERLAYS` und `EVENTS` sind fachlich wichtig, aber im Dateisystem und in den Build-Kontrakten noch nicht hart genug getrennt.
- `config.json` / optionale Startkonfiguration ist geplant, aber nicht implementiert.
- DoA-Live-Integration ist geplant und teilweise vorbereitet, aber noch nicht umgesetzt.

## Zustandseinschaetzung

Der Projektstand ist weiterentwickelbar und technisch wertvoll. Die Trennung von Effektdefinitionen und Hauptlogik ist bereits deutlich fortgeschritten. Der groesste akute Risikobereich war nicht die Runtime selbst, sondern Git-/Worktree-Chaos, uneindeutige Doku-Staende und die inkonsistente Behandlung von Effekt-Source-Artefakten im Build-Bereich.

