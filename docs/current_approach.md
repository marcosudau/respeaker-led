# Aktueller Ansatz Im Repo

Stand: 2026-04-19

Es gibt nur noch einen aktiven Produktpfad im Repo:

- einen dauerhaft laufenden lokalen Controller-Service
- Steuerung per CLI oder HTTP

Fuer die aktuelle Release-Strecke ist dieser Service auf den lokalen Unterprozess-Betrieb ausgelegt.

## Einstiegspunkte

Die relevanten Einstiegspunkte sind:

- `main.py`
- `src/interfaces/cli.py`
- `src/interfaces/api.py`
- `src/services/service.py`
- `src/engine/runtime.py`

## Wichtige Trennung

Damit keine Begriffe durcheinandergehen, gilt heute diese klare Aufteilung:

- `build-tools/` ist der normale Build fuer EXE und Release-Bundle.
- `tools/effect_building/` ist das separate Effekt-Building.
- `src/` enthaelt den laufenden Service, Runtime, Registry und Loader.

Der normale Build erzeugt die Service-EXE und das Release-Bundle. Er konsumiert nur fertige `.lefx`- und `.lefxset`-Artefakte, die ueber `build-tools/build_config.json` konfiguriert sind.

## Datenfluss

Der Service arbeitet intern ueber eine feste Pipeline:

```mermaid
flowchart LR
    A["CLI / API / STT / Presets"] --> B["ControllerCommandNormalizer"]
    B --> C["NormalizedCommand"]
    C --> D["EffectInvocation"]
    D --> E["LayerStore"]
    E --> F["SceneComposer"]
    F --> G["SceneRenderer"]
    G --> H["FrameAdapter"]
```

## Zentrale Service-Faehigkeiten

Der Service kann heute direkt:

- Status lesen und health-checken
- Basiszustaende setzen und loeschen
- Events ausloesen
- Countdowns starten, aktualisieren und abbrechen
- Richtungsmarker setzen und loeschen
- Brightness und Enabled schalten
- eingebaute Effekte direkt auf Layer anwenden
- Layer gezielt leeren
- optionale Presets aktivieren
- Portverfuegbarkeit vor dem Start pruefen und optional aus einem Portpool ausweichen
- eine vorhandene aktive Instanz vor dem Neustart uebernehmen und beenden

## Verfuegbare Standardeffekte

Die aktuelle Standardbibliothek wird aus dem Effektset `default-effects.lefxset` geladen.

Die Runtime bevorzugt im Bundle `effects/default-effects.lefxset` neben der EXE. Fuer Entwicklungsstarts kennt sie zusaetzlich die in `build-tools/build_config.json` konfigurierten Builtin-Artefakte.

Wichtige IDs sind:

- `off`
- `solid_color`
- `soft_pulse`
- `blink_color`
- `progress_bar`
- `direction_indicator`
- `countdown_ring`
- `warning_flash`

Die vollstaendige Liste bekommst du ueber:

```powershell
python .\main.py list-effect-sources
python .\main.py list-effects
```

Die Einbindung von Effekt-Artefakten und die Trennung zwischen normalem Build und Effekt-Building stehen in [effects.md](effects.md).

## Finale Layer

- `BACKGROUND_STATE_LAYER`
- `STATE_LAYER`
- `MAIN_LAYER`
- `TEMP_OVERLAY_LAYER`
- `ONGOING_OVERLAY_LAYER`
- `EVENT_LAYER`

Fuer CLI und API werden kuerzere Layernamen wie `background`, `state`, `main`, `temp_overlay`, `ongoing_overlay` und `event` akzeptiert.

## Abgeschlossene Bereinigungen

- Die Runtime akzeptiert keine `legacy_visual`-Kompatibilitaet mehr.
- Die Default-Registry faellt nicht mehr auf rohe Python-Bibliothekspfade zurueck.
- Zusaetzeffekte werden ausschliesslich als `.lefx`- oder `.lefxset`-Artefakte registriert oder autodiscovered.

## Runtime-Persistenz

Der Service speichert den aktiven `BACKGROUND_STATE_LAYER` in `background_state.json` im Temp-Verzeichnis `respeaker_led_controller_runtime_state/` und stellt ihn beim Start wieder her.

Wenn keine gueltige Persistenzdatei vorhanden ist, setzt der Service als Start-Fallback einen statischen weissen Hintergrund mit `brightness=0.2`, damit das Geraet einen laufenden Service sichtbar anzeigt.

Fuer den Unterprozess-Betrieb schreibt der Service zusaetzlich `active_service.json` in dasselbe Temp-Verzeichnis.

Diese Datei enthaelt die aktive PID sowie Host und Port der laufenden Instanz und ist der vorgesehene Rueckkanal fuer Host-Anwendungen, wenn wegen eines Portpools nicht der urspruenglich angefragte Port verwendet wurde.

## Was entfernt wurde

- der direkte Effects-Engine-Pfad
- lokale Demo- und Showcase-Kommandos ausserhalb des Service-Betriebs
- rohe Builtin-Effektquellen unter `src/`
