# Development Notes

## Ziel der aktuellen Architektur

Der aktuelle Service-Kern in `src/` soll ein generischer Invocation-basierter LED-Controller sein und moeglichst wenig App-Semantik tragen.

Dafuer gelten folgende Leitlinien:

- `LayerStore` plus `EffectInvocation` sind die Source of Truth fuer aktive Service-Effekte
- alle fachlichen Eingaben laufen zuerst durch `ControllerCommandNormalizer`
- `ControllerRuntime` enthaelt Engine-Mutationen und Statuslogik
- `ControllerService` kuemmert sich um Worker, API, Prozess-Lifecycle und Fallbacks
- dateibasierte Service-Effekte leben in `led_effects/effects/`
- `SceneComposer`, `SceneRenderer` und `FrameAdapter` bilden die feste Frame-Pipeline
- Hardware-Ausgabe bleibt auf Vollring-Frames fuer den ReSpeaker ausgelegt

## Aktueller Zuschnitt des Repos

Der aktive Produktionspfad liegt vollstaendig in `src/`.

Er wird ergaenzt durch:

- `led_effects/effects/` fuer die eigentlichen Effektmodule
- `led_effects/preset_packs/` fuer optionale Presets
- `python_control/` fuer den Hardware-Zugriff

## Preset-Discovery

Preset-Packs liegen unter `led_effects/preset_packs/<name>/`.

Ein Pack besitzt mindestens:

- `preset.yaml`
- `preset.py`

Optional:

- `sample.json`

`preset.py` exportiert `build_preset(spec)` und gibt `PresetBuildResult` zurueck.

Wichtig:

- Presets laufen heute innerhalb derselben Runtime
- sie duerfen aktuell aber noch Legacy-Visuals liefern
- damit ist die Engine vereinheitlicht, die Preset-Migration aber noch nicht maximal sauber abgeschlossen

## API und CLI

API und CLI arbeiten beide gegen denselben `ControllerRuntime`, aber nur ueber den aeusseren `ControllerService`.

Die API bleibt bewusst klein und deckt nur die generischen Kernaktionen ab:

- Effekte auflisten
- Status lesen und Service pingen
- Basiszustand setzen oder zuruecksetzen
- direkte Effekte setzen und Layer leeren
- Events ausloesen
- Countdown starten, aktualisieren und abbrechen
- Richtung, Brightness und Enabled setzen
- Presets optional laden und aktivieren

Die Default-Registry scannt `led_effects/effects/` beim Start automatisch.

## Lokale Integrationen

- Externe Prozesse verwenden `LocalControllerClient`.
- STT-Integrationen laufen ueber `SttLedAdapter` und bleiben ausserhalb des Cores.
- Best-Effort ist fuer externe Aufrufer Standard; nur CLI-Kommandos schalten auf striktes Fehlerverhalten um.

## Bewusst verschoben

- oeffentliche CLI/API-Verwaltung fuer Registry-Library-Pfade und Reload
- vollstaendige Preset-Migration von `Visual`-Kompatibilitaet auf reine `effect_id`-Invocations

## Background-State-Persistenz

- `BACKGROUND_STATE_LAYER` wird ueber `runtime_state/background_state.json` persistiert.
- Beim Service-Start wird zuerst versucht, den letzten persistierbaren Background-State wiederherzustellen.
- Wenn keine gueltige Persistenzdatei vorhanden ist, wird ein gedimmter weisser `solid_color`-Fallback gesetzt.
- Transiente Servicezustandsanzeigen wie `offline` oder `service_stopping` werden nicht in diese Persistenz geschrieben.
