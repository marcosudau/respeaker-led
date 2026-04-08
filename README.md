# reSpeaker LED Controller Engine

Dieses Repo hat zwei Hauptnutzungen:

- **direkt lokal LEDs anzeigen**
- **einen laufenden lokalen Controller per CLI/API steuern**

Der wichtigste Punkt fuer den Einstieg:

- du musst **nicht** erst Architektur, Layer, API, Presets und interne Ordner verstehen, um Licht auf dem Ring zu sehen

## Wo du anfangen solltest

Wenn du einfach nur LEDs sehen willst:

- [docs/getting_started.md](docs/getting_started.md)
- [docs/effects_engine_2_minuten.md](docs/effects_engine_2_minuten.md)

Wenn du eigene Effekte definieren willst:

- [docs/effects_engine_tutorial.md](docs/effects_engine_tutorial.md)
- [docs/reference.md](docs/reference.md)

Wenn du erstmal verstehen willst, wie das Repo sortiert ist:

- [docs/layers.md](docs/layers.md)

Wenn du den laufenden Service fernsteuern willst:

- [docs/api_guide.md](docs/api_guide.md)

## Projektstruktur in kurz

- `docs/` ist die normale Benutzer-Doku
- `docs/dev/` ist die Entwickler-Doku
- `led_effects/effects_engine/` ist die direkte Effects Engine
- `led_effects/preset_packs/` sind optionale Erweiterungspacks
- `src/` ist der lokale Controller-Prozess mit API, CLI und Runtime
- `python_control/` ist der Low-Level-Hardwarezugriff

## Was du am Anfang ignorieren kannst

Wenn du einfach Effekte anzeigen willst, kannst du erstmal ignorieren:

- `docs/dev/`
- Preset-Packs
- `src/`-Interna
- interne Layer-Modelle

## Quickstart

### Tests ausfuehren

```powershell
pytest -q
```

### Preview-Demo ohne Hardware

```powershell
python .\main.py --no-device demo --seconds 5
```

### Lokalen Controller-Prozess starten

```powershell
python .\main.py --no-device serve --host 127.0.0.1 --port 8765
```

### Laufenden Controller ansteuern

```powershell
python .\main.py status
python .\main.py set-state listening
python .\main.py emit-event trigger_received --duration-ms 900 --source manual
python .\main.py start-countdown 5000 --remaining-ms 2000 --follow-up-state transcribing
python .\main.py set-direction 120
```

### Optionale Effekt-Packs auflisten

```powershell
python .\main.py list-presets
```

## Wichtige Hinweise

- Discovery ist optional. Der Core rendert auch ohne Effekt-Packs.
- Wenn echte Hardware fehlt, faellt der Service sicher auf Console-Preview zurueck.
- Externe Aufrufer sollten den Best-Effort-Client verwenden, nicht den Hardware-Adapter.
- `pytest -q` bleibt der Standard-Testlauf.

## Weiterfuehrende Doku

- [docs/getting_started.md](docs/getting_started.md)
- [docs/effects_engine_2_minuten.md](docs/effects_engine_2_minuten.md)
- [docs/effects_engine_tutorial.md](docs/effects_engine_tutorial.md)
- [docs/layers.md](docs/layers.md)
- [docs/effects_engine.md](docs/effects_engine.md)
- [docs/presets.md](docs/presets.md)
- [docs/reference.md](docs/reference.md)
- [docs/api_guide.md](docs/api_guide.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)
- [docs/dev/index.md](docs/dev/index.md)
- [docs/dev/effects_engine_dev.md](docs/dev/effects_engine_dev.md)
- [docs/dev/public_entry_points.md](docs/dev/public_entry_points.md)
