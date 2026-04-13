# Development Notes

## Ziel der aktuellen Architektur

Der aktuelle Service-Kern in `src/` soll ein generischer Invocation-basierter LED-Controller sein und moeglichst wenig App-Semantik tragen.

Dafuer gelten folgende Leitlinien:

- `LayerStore` plus `EffectInvocation` sind die Source of Truth fuer aktive Service-Effekte
- alle fachlichen Eingaben laufen zuerst durch `ControllerCommandNormalizer`
- `ControllerRuntime` enthaelt Engine-Mutationen und Statuslogik
- `ControllerService` kuemmert sich um Worker, API, Prozess-Lifecycle und Fallbacks
- Standardeffekte werden in `src/led_effects/effects/` als Python-Buildquellen gepflegt und als `.lefx`- bzw. `.lefxset`-Artefakte ausgeliefert
- `SceneComposer`, `SceneRenderer` und `FrameAdapter` bilden die feste Frame-Pipeline
- Hardware-Ausgabe bleibt auf Vollring-Frames fuer den ReSpeaker ausgelegt

## Aktueller Zuschnitt des Repos

Der aktive Produktionspfad liegt vollstaendig in `src/`.

Er wird ergaenzt durch:

- `src/led_effects/effects/` fuer die Python-Buildquellen der Standardeffekte und das publizierte `default-effects.lefxset`
- `src/led_effects/packages/` fuer optionale zusaetzliche Effektartefakte
- `src/python_control/` fuer den Hardware-Zugriff

## Effekt-Presets und Commands

Effekt-Presets und Commands liegen heute nicht mehr als separates Preset-Pack-System im Repo.

Sie werden in `.lefx`- und `.lefxset`-Artefakten eingebettet und ueber folgende Wege sichtbar:

- `list_effect_presets(...)` bzw. `GET /api/v1/effects/{source_id}/{effect_id}/presets`
- `list_effect_commands(...)` bzw. `GET /api/v1/effects/{source_id}/{effect_id}/commands`
- `apply_effect_preset(...)` bzw. `POST /api/v1/effect-presets/{source_id}/{preset_id}/apply`
- `invoke_effect_command(...)` bzw. `POST /api/v1/commands/{source_id}/{command_name}`

Wichtig:

- Presets und Commands referenzieren reine Effekt-IDs und Parameter
- `legacy_visual` spielt im aktuellen Modell keine Rolle mehr
- die Default-Quelle `default-effects` bringt bereits eingebettete Presets und Commands mit

## API und CLI

API und CLI arbeiten beide gegen denselben `ControllerRuntime`, aber nur ueber den aeusseren `ControllerService`.

Die API bleibt bewusst klein und deckt nur die generischen Kernaktionen ab:

- Effekte auflisten
- Effektquellen, Effekt-Presets und Commands auflisten
- Status lesen und Service pingen
- Basiszustand setzen oder zuruecksetzen
- direkte Effekte setzen und Layer leeren
- Events ausloesen
- Countdown starten, aktualisieren und abbrechen
- Richtung, Brightness und Enabled setzen

Die Default-Registry laedt beim Start `default-effects.lefxset`. Ueber CLI und API koennen weitere `.lefx`- und `.lefxset`-Artefakte registriert oder neu geladen werden.

## Lokale Integrationen

- Externe Prozesse verwenden `LocalControllerClient`.
- STT-Integrationen laufen ueber `SttLedAdapter` und bleiben ausserhalb des Cores.
- Best-Effort ist fuer externe Aufrufer Standard; nur CLI-Kommandos schalten auf striktes Fehlerverhalten um.

## Bewusst verschoben

- zusaetzliche Bundle- und App-spezifische Effektquellen jenseits der vorhandenen `.lefx`- und `.lefxset`-Beispiele
- weitergehende Host-spezifische Command-Konventionen oberhalb des generischen Effektmodells

## Background-State-Persistenz

- `BACKGROUND_STATE_LAYER` wird ueber `runtime_state/background_state.json` persistiert.
- Beim Service-Start wird zuerst versucht, den letzten persistierbaren Background-State wiederherzustellen.
- Wenn keine gueltige Persistenzdatei vorhanden ist, wird ein gedimmter weisser `solid_color`-Fallback gesetzt.
- Transiente Servicezustandsanzeigen wie `offline` oder `service_stopping` werden nicht in diese Persistenz geschrieben.
