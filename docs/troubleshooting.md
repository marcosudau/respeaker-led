# Troubleshooting

## Service nicht erreichbar

- laeuft `python .\main.py --no-device serve --host 127.0.0.1 --port 8765`?
- antwortet `python .\main.py ping`?
- stimmen Host und Port?
- wurde ein Ersatzport aus `--port-pool` gewaehlt?
- welchen Port nennt `active_service.json`?

## Tests schlagen fehl

- `pytest -q` aus dem Projekt-Root ausfuehren
- bei Importfehlern die aktive Python-Umgebung und den Arbeitsordner pruefen
- Test-Caches liegen unter `tests/.cache` und werden automatisch bereinigt

## Ziel wird nicht gefunden

```powershell
python .\main.py list states
python .\main.py list overlays
python .\main.py list events
python .\main.py list presets
python .\main.py show <id>
```

Falls ein Artefakt gerade neu gebaut wurde, den Service neu starten oder
`python .\main.py reload-effect-sources` ausfuehren.

## `set` oder `emit` wird abgewiesen

- passt die Operation zum Typ?
- ist `--config` gueltiges JSON?
- sind alle Parameternamen in `show <id>` deklariert?
- liegen Zahlen innerhalb der angegebenen Grenzen?
- besitzt ein endlicher Typ die notwendige Dauer?

Die API liefert bei Parameterfehlern HTTP 422 mit Feldname, Fehlercode und
erwartetem Vertrag.

## Kontrolliertes Overlay laesst sich nicht aktualisieren

- wurde es mit einem nichtleeren `--channel` gesetzt?
- wird bei `update` derselbe Channel verwendet?
- stehen die Werte unter `--inputs`, nicht unter `--config`?
- sind die Runtime-Eingaben in `show <id>` deklariert?

Zeitbegrenzte Overlays akzeptieren kein `update`, `off` oder `toggle`.

## Effekt ist nicht sichtbar

- steht `enabled` im Status auf `false`?
- wurde der State-Slot oder Overlay-Channel spaeter ersetzt oder geloescht?
- ist ein hoeher priorisiertes Overlay oder Event aktiv?
- enthaelt `status` gueltige `last_frame`-Daten?

## Keine Hardware-Ausgabe

- ist das ReSpeaker-Geraet verfuegbar?
- funktioniert derselbe Ablauf mit `--no-device`?
- meldet der Status `fallback_active: true`?
- der Hardwarepfad verwendet `src/python_control/xvf_host.py`

## Background-State nach Neustart unerwartet

- Inhalt von `background_state.json` pruefen
- nur der Background-Slot wird persistiert
- bei fehlender oder ungueltiger Datei startet `solid_color` gedimmt in Weiss
- transiente Servicemodi werden absichtlich nicht persistiert
