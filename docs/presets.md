# Effekt-Presets Und Commands

Diese Seite ist bewusst als **optionales** Thema markiert.

Wenn du einfach nur den Service starten und direkte Effekte per `apply-effect` setzen willst, brauchst du Effekt-Presets und Commands nicht.

## Was Effekt-Presets und Commands sind

Effekt-Presets und Commands sind eingebettete Metadaten innerhalb von `.lefx`- und `.lefxset`-Artefakten.

Sie sind sinnvoll, wenn du:

- wiederverwendbare Effektparameter unter einer stabilen ID anbieten willst
- haeufige On-Off- oder Toggle-Aktionen als Command kapseln willst
- einer Host-Anwendung ein kleineres Befehlsvokabular geben willst als rohe Effektparameter

## Was sie nicht sind

- kein separates Preset-Pack-System im Dateisystem
- kein eigener Betriebsweg neben dem laufenden Service
- nicht noetig, um `apply-effect`, `set-state` oder `emit-event` zu verwenden

## Wo sie heute liegen

Effekt-Presets und Commands entstehen beim Packaging aus Effektquellen und werden zusammen mit dem Effekt als Artefakt ausgeliefert.

Typische Quellen sind:

- `src/led_effects/effects/default-effects.lefxset` fuer die Default-Bibliothek
- zusaetzliche `.lefx`- oder `.lefxset`-Dateien unter `src/led_effects/packages/`
- Bundle-Dateien unter `effects/` und `packages/` neben der EXE

## Discovery

Mit der CLI:

- `python .\main.py list-effect-sources`
- `python .\main.py list-effect-presets default-effects::soft_pulse`
- `python .\main.py list-effect-commands default-effects::soft_pulse`
- `python .\main.py list-commands --source default-effects`

Mit der API:

- `GET /api/v1/effect-sources`
- `GET /api/v1/effects/{source_id}/{effect_id}/presets`
- `GET /api/v1/effects/{source_id}/{effect_id}/commands`
- `GET /api/v1/commands/{source_id}`

## Aktivierung

Effekt-Preset anwenden:

- CLI: `python .\main.py apply-effect-preset default-effects::effect_soft_pulse_main`
- API: `POST /api/v1/effect-presets/default-effects/effect_soft_pulse_main/apply`

Command ausloesen:

- CLI: `python .\main.py invoke-command default-effects effect_soft_pulse_accent`
- API: `POST /api/v1/commands/default-effects/effect_soft_pulse_accent`

## Wenn du das eigentlich gar nicht brauchst

Dann geh lieber hierhin:

- [Hier anfangen](getting_started.md)
- [CLI und API](api_guide.md)
- [Aktueller Ansatz im Repo](current_approach.md)
