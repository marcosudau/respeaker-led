# respeaker-led

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**respeaker-led** ist die offizielle Python-Bibliothek und CLI-Steuerung für den **reSpeaker XVF3800 LED-Ring**.

Das Paket bietet sowohl einen automatischen Hintergrund-Daemon (mit robuster USB-Auto-Reconnect-Logik) als auch eine direkte Einbettung (`ControllerService`) in eigene Python-Anwendungen (z. B. Sprachassistenten oder STT-Pipelines).

---

## Features

- 🔌 **USB Auto-Reconnect & Resilienz**: Automatischer Verbindungsaufbau, Heartbeat-Überwachung und Wiederherstellung des Hardware-Modus bei Kabeltrennung.
- 🐍 **Direkte Python-Einbettung**: `ControllerService` im selben Prozess ausführen — ohne HTTP-Latenz oder externe Services.
- 💻 **CLI-Steuerung mit Auto-Daemon**: Befehle wie `respeaker-led set state listening` starten den Hintergrunddienst bei Bedarf automatisch.
- 🎨 **Umfangreiche Effekt-Bibliothek**: 24 Zustände (Listening, Processing, Speaking, etc.), 20 flüchtige Events, 13 Overlays (DOA-Richtungsanzeige, Countdown-Ring) und Preset-Support.
- 🖼️ **Virtueller Vorschau-Modus**: Kann auch ohne angeschlossene Hardware zur Entwicklung verwendet werden (`console-preview`).

---

## Installation

```bash
pip install respeaker-led
```

### Optional: GUI-Demo (PySide6)

Wenn du das mitgelieferte PySide6-Beispiel zur Echtzeit-Visualisierung im Fenster ausführen möchtest:

```bash
pip install respeaker-led[demo]
```

---

## Nutzung 1: Direkte Einbettung in Python-Apps (Embedded)

Für Sprachassistenten, STT-Pipelines oder eigene GUI-Anwendungen:

```python
from respeaker_led import ControllerService

# Service im selben Prozess starten
with ControllerService(use_device=True) as service:
    # 1. Hauptzustand setzen
    service.set_state_target("listening")

    # 2. Kurzes Event auslösen (z. B. Wake-Word)
    service.emit_event_target("short_flash", {"color": "0xFFFFFF"})

    # 3. Overlay setzen (z. B. DOA-Richtungsanzeige)
    service.set_overlay_target("direction_indicator", channel="doa", inputs={"angle": 180.0})

    # ... Anwendungslogik ...

    service.set_state_target("processing")
```

👉 **Vollständiges Anwender-Handbuch & Effekt-Tabellen:**  
Siehe [docs/integration_guide.md](docs/integration_guide.md)

---

## Nutzung 2: CLI-Befehle

Nach der Installation stehen dir folgende Konsolenbefehle zur Verfügung:  
`respeaker-led`, `led-controller`, `ledctl`, `respeaker`, `led`

```bash
# Zustand setzen (startet den Daemon automatisch im Hintergrund)
respeaker-led set state listening

# Hintergrund-Zustand ändern
respeaker-led set state solid_color --params '{"color":"0x00AAFF"}'

# Kurzes Event auslösen
respeaker-led emit event short_flash --params '{"color":"0xFFFFFF"}'

# Helligkeit regeln
respeaker-led set brightness 0.5

# Status abfragen
respeaker-led status

# Daemon explizit als Service im Vordergrund betreiben
respeaker-led serve
```

---

## Nutzung 3: PySide6 Demo-Anwendung

Das Repository enthält eine einsatzbereite PySide6 GUI-Anwendung mit einem virtuellen 12-LED-Ring in Echtzeit:

```bash
# Virtueller Modus (ohne Hardware):
python examples/pyside6_demo.py

# Mit echter USB-Hardware:
python examples/pyside6_demo.py --device
```

---

## Entwicklung & Tests

Für die lokale Entwicklung mit `uv`:

```bash
# Abhängigkeiten synchronisieren
uv sync --all-groups

# Test-Suite ausführen (192 Tests)
uv run pytest -q

# Paket lokal bauen
uv build
```

---

## Dokumentation

- 📖 [Integration Guide (Python-Einbettung & Effekt-Katalog)](docs/integration_guide.md)
- 🛠️ [CLI Guide](docs/cli_guide.md)
- 🔌 [API Guide](docs/api_guide.md)
- 🏗️ [Architektur-Dokumentation](docs/dev/architecture.md)

---

## Lizenz

MIT License © [Marco Sudau](https://github.com/marcosudau)
