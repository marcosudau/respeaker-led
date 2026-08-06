# Minimalinvasiver Plan: Direct Embedding des `ControllerService` in Host-Anwendungen

## Zielsetzung

Eine Host-Anwendung (wie eine STT- / Sprachassistent-App) soll den LED-Controller **direkt im selben Python-Prozess** ausführen. 

Es werden **keine neuen Wrapper-Klassen, geänderte Methodennamen oder abgeänderte Datenverträge** eingeführt. Der bestehende `ControllerService` stellt bereits die vollständige, geprüfte Python-API mit allen bestehenden Verträgen (V2 Target-Resolution, Slots, Channels, Overlays, Countdown, Events) bereit.

---

## 1. Kernkonzept

Die Host-Anwendung instanziiert und startet `ControllerService` direkt als Python-Objekt. Der Service betreibt seine bestehende Renderschleife in einem separaten Thread und nutzt den `UsbConnectionManager` für die automatische USB-Verwaltung.

```
  STT-Anwendung (Host-Prozess)
  ├── Audio-Pipeline / STT-Engine
  └── ControllerService (bestehendes Modul)
      ├── Render-Thread (@ 8 FPS oder konfigurierbar)
      ├── UsbConnectionManager (Auto-Reconnect)
      └── Direkte Python-Aufrufe ohne HTTP / IPC
```

---

## 2. Minimalinvasive Anpassungen am Projekt

### 1. Paket-Export in `src/__init__.py`
Direktes Bereitstellen von `ControllerService` auf Paketebene:

```python
from .services.service import ControllerService

__all__ = [
    "__version__",
    "ControllerService",
    # ...
]
```

### 2. Ergänzung von Context-Manager-Support in `ControllerService`
Direktes Hinzufügen von `__enter__` und `__exit__` zur bestehenden Klasse `ControllerService` in `src/services/service.py`:

```python
def __enter__(self) -> ControllerService:
    self.start()
    return self

def __exit__(self, exc_type, exc_val, exc_tb) -> None:
    self.stop()
```

---

## 3. Direkte Nutzung in der Host-Anwendung (Beispiel)

Die Host-Anwendung nutzt ausschließlich die bestehenden, unveränderten Methoden des `ControllerService`:

```python
from respeaker_led import ControllerService

# Option A: Als Context Manager
with ControllerService(fps=8.0, use_device=True) as service:
    service.set_state_target("listening")
    # ... STT-Verarbeitung ...
    service.emit_event_target("trigger_received", {"duration_ms": 900})
    service.set_state_target("processing")
    # ...

# Option B: Über den Lifecycle der Host-App (start / stop)
class STTApplication:
    def __init__(self):
        self.led_service = ControllerService(fps=8.0, use_device=True)

    def start(self):
        self.led_service.start()
        self.led_service.set_state_target("idle")

    def on_wake_word(self):
        self.led_service.emit_event_target("trigger_received")
        self.led_service.set_state_target("listening")

    def on_processing(self):
        self.led_service.set_state_target("processing")

    def on_stop(self):
        self.led_service.stop()
```

---

## 4. Vorteile dieser Lösung

1. **Null-Overhead**: Kein zusätzlicher Wrapper-Code, der gewartet werden muss.
2. **100% Vertragstreue**: CLI, API (HTTP) und direkte Python-Einbettung nutzen exakt dieselben Schnittstellen, Parameter und Bezeichnungen.
3. **Volle Kontrolle**: Die Host-App kann jederzeit `get_status()`, `snapshot()` oder spezifische Target-Operationen (`set_state_target`, `set_overlay_target`, `emit_event_target`) aufrufen.
