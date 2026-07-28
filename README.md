# reSpeaker LED Controller Service

Dieses Repo konzentriert sich auf einen dauerhaft laufenden lokalen LED-Service, der per CLI oder HTTP gesteuert wird.

Alle aktiven Einstiegspunkte laufen ueber `main.py`, `src/interfaces/cli.py`, `src/interfaces/api.py` und `src/services/service.py`.

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

Die lokale Entwicklungs- und CI-Umgebung ist auf `uv` und Python 3.12 ausgerichtet.

### 1. Abhaengigkeiten synchronisieren

```powershell
uv sync --all-groups
```

### 2. Tests ausfuehren

```powershell
uv run pytest -q
```

Pytest buendelt temporaere Dateien, den Pytest-Cache, Python-Bytecode und die nur fuer
Tests gebauten Effektartefakte unter `tests/.cache/`. Der Ordner wird nach jeder
Testsitzung automatisch entfernt.

## Building

Der Standard-Build laeuft ueber [build-tools/build.py](build-tools/build.py) und liest seine Schalter und Effektquellen aus [build-tools/build_config.json](build-tools/build_config.json).

```powershell
uv run python build-tools/build.py --force
```

Standardmaessig werden die Artefakte mit Version gebaut:

- `dist/led_controller_service_<version>.exe`
- `dist/release_bundle/led_controller_service_<version>_windows_x64.zip`

Mit `--no-version` werden dieselben Artefakte ohne Versionssuffix erzeugt.

Die Detail-Doku fuer Build-Skripte, Konfiguration, Cleanup und Bundle-Template steht in [build-tools/README.md](build-tools/README.md).

## Release

Die einzige Versionsquelle ist [build-tools/version.py](build-tools/version.py); lokale Builds lesen diese Datei nur, sie aendern sie nicht.

Fuer einen GitHub-Release muss ein Tag `vX.Y.Z` erstellt werden, dessen Version exakt zu `build-tools/version.py` passt.

Lokal entsteht das Release-Bundle als ZIP unter `dist/release_bundle/`; im Release-Workflow wird genau dieses ZIP als Release-Artefakt veroeffentlicht.

Die Release-Regeln und der Tag-basierte Ablauf stehen in [build-tools/RELEASE.md](build-tools/RELEASE.md).

## Projektstruktur in kurz

- `src/` enthaelt die fachlich gegliederte Paketstruktur fuer CLI, API, Service, Runtime, Renderer und Effect-Registry.
- `build-tools/` enthaelt den kompletten normalen Build-Prozess, das PyInstaller-Spec-File, die Versionsquelle und das Release-Bundle-Template.
- `tools/effect_building/` enthaelt das separate Effekt-Building und liefert die `.lefx`- und `.lefxset`-Artefakte, die ueber `build-tools/build_config.json` eingebunden werden.
- zur Laufzeit schreibt der Service `background_state.json` und `active_service.json` in ein Temp-Verzeichnis unter `respeaker_led_controller_runtime_state/`.
- `logs/led_controller.log` enthaelt das einfache Basislogging des Service.
- `src/python_control/` enthaelt den Low-Level-Hardwarezugriff.
- `docs/` enthaelt die verbleibende Nutzer-Doku.
- `docs/dev/` enthaelt die interne Entwickler-Doku.
- `tests/` prueft den Service-Pfad, API, CLI, Runtime und Build-Tooling.

## Wichtige Hinweise

- `--no-device` startet den Service ohne echte Hardware und previewt Frames in der Konsole.
- Ohne gespeicherten Background-State startet der Service mit einem gedimmten weissen Grundlicht als Online-Anzeige.
- Beim Start prueft der Service die gewuenschte Portbelegung vorab; optional kann er auf einen Port aus `--port-pool` ausweichen.
- Es ist nur eine aktive Instanz vorgesehen; eine neu gestartete Instanz versucht eine vorhandene alte Instanz zuerst zu beenden.
- Der gewaehlt gestartete Host/Port wird fuer Host-Anwendungen in `active_service.json` im Temp-Verzeichnis abgelegt und beim Start zusaetzlich als JSON auf stdout ausgegeben.
- Start und Stop des Service werden durch drei schnelle Vollring-Blinks signalisiert: Gruen beim Start, Rot beim Stop.
- Fuer echte Fernsteuerung muessen Service und Steuer-Kommandos in getrennten Terminals laufen.
- Optional kannst du statt `main.py` auch `python -m src ...` verwenden.

## Weiterfuehrende Doku

- [docs/getting_started.md](docs/getting_started.md)
- [docs/api_guide.md](docs/api_guide.md)
- [docs/effects.md](docs/effects.md)
- [docs/current_approach.md](docs/current_approach.md)
- [docs/presets.md](docs/presets.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)
- [docs/dev/index.md](docs/dev/index.md)
