# led_effects

Dieser Ordner enthaelt die dateibasierte Effektbibliothek und optionale Preset-Packs fuer den laufenden Service.

## Was hier wo liegt

### `effects/`

Die eigentlichen Effektmodule des Service.

Jede Python-Datei in diesem Ordner kann eine oder mehrere `BaseEffect`-Klassen bereitstellen.

Die Default-Registry scannt diesen Ordner automatisch beim Start des Service.

### `preset_packs/`

Optionale Erweiterungen fuer den Controller-Service in `src/`.

Wenn du den Service nur starten und direkte Built-in-Effekte setzen willst, brauchst du diesen Ordner nicht.

Mehr dazu:

- `docs/effects.md`
- `docs/presets.md`
- `docs/getting_started.md`
