# led_effects

Dieser Ordner ist kein loser Sammelplatz fuer Effektdateien, sondern ein Oberbegriff fuer zwei verschiedene LED-Themen:

- `effects_engine/` enthaelt die eigentliche Engine und ihren Code
- `preset_packs/` enthaelt optionale Erweiterungspacks

## Wenn du nur LEDs anzeigen willst

Dann musst du hier nicht alles lesen.

Der bessere Einstieg ist:

- `docs/getting_started.md`
- `docs/effects_engine_2_minuten.md`
- `docs/effects_engine_tutorial.md`

## Was hier wo liegt

### `effects_engine/`

Framework-Code fuer die direkte LED-Steuerung:

- einfache API
- Effektdefinitionen
- Controller
- JSON/YAML-Loader
- Hardware-Backend

### `preset_packs/`

Optionale Pack-Erweiterungen fuer den `src/`-Controller.

Nicht noetig fuer den normalen Einstieg.

### `.old/`

Archiv- oder Altmaterial. Kein normaler Einstiegspunkt.
