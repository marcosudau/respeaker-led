# Troubleshooting

## Ich weiss nicht, welchen Weg ich ueberhaupt nehmen soll

Das ist der haeufigste Startfehler.

- fuer direktes Licht in Python: [effects_engine_2_minuten.md](effects_engine_2_minuten.md)
- fuer eigene JSON/YAML-Dateien: [effects_engine_tutorial.md](effects_engine_tutorial.md)
- fuer Fernsteuerung eines laufenden Controllers: [api_guide.md](api_guide.md)
- fuer Repo-Orientierung: [layers.md](layers.md)

## Muss ich JSON/YAML an die API schicken?

Nein.

- JSON/YAML-Dateien werden lokal in Python geladen
- API und CLI steuern einen laufenden Controller-Service

## Tests schlagen fehl

- zuerst `pytest -q` aus dem Projekt-Root laufen lassen
- bei Importfehlern pruefen, ob du wirklich aus dem Projekt-Root startest
- bei Discovery-Fehlern Manifest und Modul des Preset-Packs kontrollieren

## Kein Effekt in der Preview sichtbar

- wurde `--no-device` gesetzt?
- wird vielleicht die falsche Schnittstelle benutzt, obwohl eigentlich nur ein lokaler Effekt angezeigt werden soll?
- wurde per CLI oder API wirklich ein Basiszustand, Event oder Countdown gesetzt?
- liefert der Snapshot unter `GET /api/v1/status` gueltige `last_frame`-Daten?
- ist `enabled` im Status eventuell auf `false` gesetzt?

## Der lokale Controller ist nicht erreichbar

- laeuft `python .\main.py --no-device serve` noch?
- antwortet `python .\main.py ping`?
- nutzt der Client den richtigen `--host` und `--port`?
- fuer externe Tools den Best-Effort-Client aus `src/client.py` statt direkter Hardware-Nutzung verwenden

## Preset wird nicht gefunden

- liegt der Ordner unter `led_effects/preset_packs/`?
- existieren `preset.yaml` und `preset.py`?
- sind `id` und `command` eindeutig?
- gibt `build_preset(spec)` wirklich ein `PresetBuildResult` zurueck?

## Keine Hardware-Ausgabe

- pruefe, ob das ReSpeaker-Geraet verfuegbar ist
- starte fuer lokale Verifikation zuerst mit `--no-device`
- der Hardware-Pfad nutzt weiterhin `python_control/xvf_host.py`
- wenn die Hardwareinitialisierung fehlschlaegt, bleibt der Service erreichbar und meldet `fallback_active: true`
