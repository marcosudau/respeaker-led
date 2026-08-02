# Schnellstart

## 1. Service ohne Hardware starten

```powershell
python .\main.py --no-device serve --host 127.0.0.1 --port 8765
```

Das Terminal bleibt offen. Der Service gibt gerenderte Frames als
Konsolenvorschau aus.

## 2. Verbindung pruefen

In einem zweiten Terminal:

```powershell
python .\main.py ping
python .\main.py status
```

## 3. Verfuegbare Ziele entdecken

```powershell
python .\main.py list states
python .\main.py list overlays
python .\main.py list events
python .\main.py list presets
python .\main.py show soft_pulse
```

Die Listen sind standardmaessig kurz. `--details` zeigt Parameter,
Lebenszyklus und Metadaten.

## 4. State setzen

```powershell
python .\main.py set state soft_pulse --config '{"color":"blau","period_ms":1600}'
python .\main.py status
```

Als persistenter Grundzustand:

```powershell
python .\main.py set state solid_color --slot background --config '{"color":"#224466"}'
```

## 5. Overlay setzen und aktualisieren

```powershell
python .\main.py set overlay direction_indicator --channel doa --inputs '{"direction":120}'
python .\main.py update overlay doa --inputs '{"direction":240}'
python .\main.py clear overlay doa
```

## 6. Event ausloesen

```powershell
python .\main.py emit event warning_flash --config '{"color":"rot","duration_ms":900}'
```

## 7. State abschalten

```powershell
python .\main.py set state soft_pulse --off
python .\main.py clear state --slot background
```

Ohne Aktionsflag bedeutet `set` immer `on`. Fuer Umschalten steht
`--toggle` zur Verfuegung.

## 8. Service beenden

```powershell
python .\main.py shutdown
```

## Weiter

- [CLI-Referenz](cli_guide.md)
- [HTTP-API-Referenz](api_guide.md)
- [Effekte und Artefakte](effects.md)
- [Troubleshooting](troubleshooting.md)
- [Aktuelle Architektur](dev/architecture.md)
