# Optionale Preset-Packs

Diese Seite ist bewusst als **optionales** Thema markiert.

Wenn du einfach nur Effekte anzeigen oder eigene JSON/YAML-Dateien definieren willst, brauchst du Preset-Packs nicht.

## Was Preset-Packs sind

Preset-Packs sind eine Erweiterungsschicht fuer den laufenden Controller in `src/`.

Sie sind sinnvoll, wenn du:

- wiederverwendbare Komplettpakete bauen willst
- eigene CLI/API-Kommandos fuer Presets haben willst
- ueber die normale Effect-Engine-Konfiguration hinausgehen willst

## Was Preset-Packs nicht sind

- nicht der normale Einstieg fuer einfache LED-Effekte
- nicht notwendig fuer die Effects Engine
- nicht notwendig fuer JSON/YAML-Effektdateien in `led_effects/effects_engine`

## Speicherort

Preset-Packs werden unter `led_effects/preset_packs/<preset_name>/` erwartet.

## Minimale Struktur

- `preset.yaml`
- `preset.py`
- optional `sample.json`

## Aktivierung

- lokal ueber die API: `POST /api/v1/presets/{preset_id}/activate`
- lokal ueber die CLI: `python .\main.py activate-preset <preset_id> --spec '{...}'`

## Wenn du das eigentlich gar nicht brauchst

Dann geh lieber hierhin:

- [Hier anfangen](getting_started.md)
- [Eigene Anzeigen Schritt fuer Schritt](effects_engine_tutorial.md)
- [Wegweiser durchs Repo](layers.md)
