# Troubleshooting

## Ich weiss nicht, womit ich anfangen soll

Fuer den aktuellen Repo-Stand gilt nur noch ein Weg:

- [Schnellstart](getting_started.md) fuer den ersten Start
- [CLI und API](api_guide.md) fuer die komplette Steuerung

## Der Service ist nicht erreichbar

Pruefe der Reihe nach:

- laeuft im ersten Terminal noch `python .\main.py --no-device serve --host 127.0.0.1 --port 8765`?
- antwortet im zweiten Terminal `python .\main.py ping`?
- stimmen `--host` und `--port` mit dem Startbefehl ueberein?
- blockiert bereits ein anderer Prozess den Port?
- wurde beim Start eventuell ein anderer Port aus `--port-pool` gewaehlt?
- steht der effektiv verwendete Port in `active_service.json` im Temp-Verzeichnis `respeaker_led_controller_runtime_state/`?

## Tests schlagen fehl

- zuerst `pytest -q` aus dem Projekt-Root laufen lassen; Test-Caches werden unter `tests/.cache` gebuendelt und am Ende automatisch entfernt
- bei Importfehlern pruefen, ob du wirklich aus dem Projekt-Root startest

## Ich sehe ohne Hardware keine Ausgabe

- starte wirklich mit `--no-device`
- lasse das Startterminal offen
- der Service previewt dann die gerenderten Frames direkt in der Konsole
- zusaetzlich kannst du mit `python .\main.py status` den letzten Frame im JSON pruefen
- ohne gespeicherte Datei startet der Background-State bewusst als gedimmtes Weiss; die Persistenz liegt in `background_state.json` im Temp-Verzeichnis `respeaker_led_controller_runtime_state/`

## Mein Effekt ist nicht sichtbar

- liefert `python .\main.py list-effects` die verwendete `effect_id` wirklich?
- wurde der Effekt auf den richtigen Layer gesetzt, zum Beispiel `main` oder `state`?
- steht `enabled` im Status vielleicht auf `false`?
- wurde der Layer spaeter durch `set-state`, `clear-layer` oder `reset` wieder ueberschrieben?
- liefert `python .\main.py status` gueltige `last_frame`-Daten?

## `apply-effect` liefert einen Fehler

- pruefe die Effect-ID mit `python .\main.py list-effects`
- pruefe den Layernamen, zum Beispiel `main`, `state` oder `event`
- pruefe, ob `--params` gueltiges JSON ist

## Effekt-Preset oder Command wird nicht gefunden

- pruefe die Quelle mit `python .\main.py list-effect-sources`
- pruefe die Effekt-ID mit `python .\main.py list-effects`
- pruefe eingebettete Presets mit `python .\main.py list-effect-presets <source_id>::<effect_id>`
- pruefe Commands mit `python .\main.py list-commands --source <source_id>`
- wenn du die Artefakte gerade neu gebaut hast, fuehre `python .\main.py reload-effect-sources` aus oder starte den Service neu

## Keine Hardware-Ausgabe

- pruefe, ob das ReSpeaker-Geraet verfuegbar ist
- starte fuer lokale Verifikation zuerst mit `--no-device`
- der Hardware-Pfad nutzt weiterhin `src/python_control/xvf_host.py`
- wenn die Hardwareinitialisierung fehlschlaegt, bleibt der Service erreichbar und meldet `fallback_active: true`

## Der neue Service startet, aber der alte lief noch

- Release 1 ist auf genau eine aktive Instanz ausgelegt
- eine neue Instanz versucht eine vorhandene alte aktive Instanz zuerst ueber deren Metadaten aus `active_service.json` zu beenden
- wenn das nicht gelingt, pruefe `active_service.json` im Temp-Verzeichnis und `logs/led_controller.log`

## Ich weiss nicht, welchen Port der gestartete Unterprozess verwendet

- lies `active_service.json` im Temp-Verzeichnis
- dort stehen PID, Host, Port und Status der aktiven Instanz
- beim Start gibt der Prozess dieselben Informationen zusaetzlich als JSON auf stdout aus

## Der Background-State wirkt nach einem Neustart anders als erwartet

- pruefe den Inhalt von `background_state.json` im Temp-Verzeichnis
- der Service restauriert den letzten persistierbaren Background-State beim Start automatisch
- wenn die Datei fehlt oder ungueltig ist, startet der Service mit `solid_color` in Weiss und `brightness=0.2`
- transiente Service-Zustaende wie `service_stopping` werden absichtlich nicht als persistierter Background-State uebernommen
