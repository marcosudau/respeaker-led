# Optionale Preset-Packs

Diese Seite ist bewusst als **optionales** Thema markiert.

Wenn du einfach nur den Service starten und direkte Built-in-Effekte setzen willst, brauchst du Preset-Packs nicht.

## Was Preset-Packs sind

Preset-Packs sind eine Erweiterungsschicht fuer den laufenden Controller in `src/`.

Sie sind sinnvoll, wenn du:

- wiederverwendbare Komplettpakete bauen willst
- wiederkehrende Effektkonfigurationen mit eigenem Namen bereitstellen willst
- Service-Effekte ueber ein gemeinsames Build-Schema zusammensetzen willst

## Was Preset-Packs nicht sind

- nicht der normale Einstieg fuer den ersten Service-Test
- nicht noetig, um `apply-effect` oder `set-state` zu verwenden

## Speicherort

Preset-Packs werden unter `src/led_effects/preset_packs/<preset_name>/` erwartet.

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
- [CLI und API](api_guide.md)
- [Aktueller Ansatz im Repo](current_approach.md)
