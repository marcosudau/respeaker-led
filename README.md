# reSpeaker LED Controller Service

Dieses Repo konzentriert sich jetzt auf genau einen Betriebsweg:

- einen dauerhaft laufenden lokalen LED-Service starten
- diesen Service per CLI oder HTTP steuern

Der direkte Effects-Engine-Pfad wurde entfernt. Alle aktiven Einstiege laufen jetzt ueber `main.py`, `src/interfaces/cli.py`, `src/interfaces/api.py` und `src/services/service.py`.

## Schnellstart

Die leichteste Schritt-fuer-Schritt-Anleitung steht hier:

- [docs/getting_started.md](docs/getting_started.md)

Die Kurzfassung:

### 1. Service starten

```powershell
python .\main.py --no-device serve --host 127.0.0.1 --port 8765
```

Optional mit Portpool fuer den Unterprozess-Betrieb:

```powershell
python .\main.py --no-device serve --host 127.0.0.1 --port 8765 --port-pool 8765-8770
```

### 2. In einem zweiten Terminal pruefen, ob er laeuft

```powershell
python .\main.py ping
python .\main.py status
```

### 3. Verfuegbare Effekte abfragen

```powershell
python .\main.py list-effects
```

### 4. Einen Effekt setzen

```powershell
python .\main.py apply-effect solid_color main --params '{"color":"0x224466"}'
python .\main.py apply-effect soft_pulse state --params '{"color":"0x33AAFF","base_color":"0x02060A","period_ms":1600}'
python .\main.py emit-event trigger_received --duration-ms 900 --source manual
```

### 5. Effekt wieder entfernen oder Service beenden

```powershell
python .\main.py clear-layer main
python .\main.py shutdown
```

## Entwicklung

Die lokale Entwicklungs- und CI-Umgebung ist auf uv und Python 3.12 ausgerichtet.

### 1. Abhaengigkeiten synchronisieren

```powershell
uv sync --all-groups
```

### 2. Tests ausfuehren

```powershell
uv run pytest -q --basetemp=.pytest_tmp
```

### 3. Release-Build lokal pruefen

```powershell
uv run pyinstaller led_controller_service.spec
uv run python .\tools\verify_release_binary.py .\dist\led_controller_service.exe
```

### 4. Release-Bundle lokal erzeugen

```powershell
uv run python .\tools\assemble_release_bundle.py --version (uv run python -c "from src.version import __version__; print(__version__)") --exe .\dist\led_controller_service.exe --output-dir .\artifacts
```

## Projektstruktur in kurz

- `src/` enthaelt die fachlich gegliederte Paketstruktur fuer CLI, API, Service, Runtime, Renderer und Effect-Registry
- `src/led_effects/effects/` enthaelt die dateibasierten Effektmodule des Service
- `src/led_effects/preset_packs/` enthaelt optionale Preset-Erweiterungen fuer den Service
- `runtime_state/background_state.json` speichert den persistierten Background-State des Service
- `runtime_state/active_service.json` enthaelt Laufzeit-Metadaten der aktiven Instanz, insbesondere Host und Port
- `logs/led_controller.log` enthaelt das einfache Release-1-Basislogging des Service
- `src/python_control/` enthaelt den Low-Level-Hardwarezugriff
- `docs/` enthaelt die verbleibende Nutzer-Doku
- `docs/dev/` enthaelt die interne Architektur-Doku
- `tests/` prueft den Service-Pfad, API, CLI und Runtime

## Wichtige Hinweise

- `--no-device` startet den Service ohne echte Hardware und previewt Frames in der Konsole.
- Ohne gespeicherten Background-State startet der Service mit einem gedimmten weissen Grundlicht als Online-Anzeige.
- Beim Start prueft der Service die gewuenschte Portbelegung vorab; optional kann er auf einen Port aus `--port-pool` ausweichen.
- Es ist nur eine aktive Instanz vorgesehen; eine neu gestartete Instanz versucht eine vorhandene alte Instanz zuerst zu beenden.
- Der gewaehlt gestartete Host/Port wird fuer Host-Anwendungen in `runtime_state/active_service.json` abgelegt und beim Start zusaetzlich als JSON auf stdout ausgegeben.
- Start und Stop des Service werden durch drei schnelle Vollring-Blinks signalisiert: Gruen beim Start, Rot beim Stop.
- Ohne Preset-Packs laeuft der Service trotzdem vollstaendig.
- Fuer echte Fernsteuerung muessen Service und Steuer-Kommandos in getrennten Terminals laufen.
- Optional kannst du statt `main.py` auch `python -m src ...` oder direkt `python .\src\cli.py ...` verwenden.

## Weiterfuehrende Doku

- [docs/getting_started.md](docs/getting_started.md)
- [docs/api_guide.md](docs/api_guide.md)
- [docs/effects.md](docs/effects.md)
- [docs/current_approach.md](docs/current_approach.md)
- [docs/presets.md](docs/presets.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)
- [docs/dev/index.md](docs/dev/index.md)
