# Integration Guide: reSpeaker LED Controller in eigene Anwendungen einbinden

Dieses Dokument richtet sich an Entwickler, die den `respeaker-led`-Controller direkt in ihre
Python-Anwendung einbetten möchten — ohne externen Service, ohne HTTP-API, vollständig im
selben Prozess.

---

## Voraussetzungen

- Python 3.12
- Windows (WinUSB-Treiber für reSpeaker XVF3800 installiert, z. B. über [Zadig](https://zadig.akeo.ie/))
- `respeaker-led` Paket installiert: `pip install respeaker-led`

---

## Schnellstart

```python
from respeaker_led import ControllerService

# Service starten (use_device=True → echte Hardware, False → virtueller Modus)
service = ControllerService(use_device=True)
service.start()

# Zustand setzen
service.set_state_target("listening")

# Wenn die Anwendung beendet wird
service.stop()
```

Mit Context Manager — garantiert sauberes Herunterfahren:

```python
from respeaker_led import ControllerService

with ControllerService(use_device=True) as service:
    service.set_state_target("listening")
    # ... Anwendungslogik ...
    service.set_state_target("processing")
# service.stop() wird automatisch aufgerufen
```

---

## Konfiguration

```python
ControllerService(
    use_device=True,      # True = USB-Hardware, False = virtueller Konsolenmodus
    fps=8.0,              # Render-Framerate (Standard: 8 FPS)
)
```

Der Service startet den USB-Verbindungsmanager automatisch. Ist das Gerät beim Start nicht
angeschlossen, wartet er im Hintergrund und verbindet sich automatisch sobald es angeschlossen wird.

---

## Zustände steuern (`set_state_target`)

Zustände sind **dauerhafte LED-Muster**, die solange aktiv sind, bis sie explizit geändert
oder gelöscht werden. Sie werden auf dem **primären Slot** des Renderers abgelegt.

```python
# Zustand aktivieren (mit optionaler Konfiguration)
service.set_state_target("listening")
service.set_state_target("soft_pulse", {"color": "0x00AAFF"})

# Zustand deaktivieren (LEDs aus / Standardzustand)
service.clear_state_target()
```

### Verfügbare Zustände

| ID | Beschreibung |
|---|---|
| `solid_color` | Alle LEDs in einer Farbe (`color`) |
| `soft_pulse` | Sanftes Pulsieren (`color`, `speed`) |
| `pulse_pattern` | Pulsmuster (`color`) |
| `blink_color` | Regelmäßiges Blinken (`color`, `on_ms`, `off_ms`) |
| `blink_pattern` | Blinksequenz (`color`) |
| `chase_dot` | Rotierender Lichtpunkt (`color`, `speed`) |
| `rotating_segment` | Rotierendes Segment (`color`, `speed`) |
| `rotating_gradient` | Rotierender Farbverlauf (`color`, `speed`) |
| `rotating_gap` | Rotierende Lücke (`color`, `speed`) |
| `fading_rotating_segment` | Abklingendes rotierendes Segment |
| `radar_sweep` | Radar-Sweep-Animation (`color`) |
| `scanner` | Scanner-Effekt (`color`) |
| `soft_pulsing_ring` | Weiches pulsierendes Ring-Muster |
| `yin_yang_spin` | Doppelter Gegenläufer (`color`) |
| — | — |
| `listening` | Hören (blau, optimiert für STT) |
| `processing` | Verarbeitung (animiert) |
| `thinking` | Nachdenken (animiert) |
| `speaking` | Sprechen/Ausgabe |
| `transcribe` | Transkription |
| `waiting` | Wartemodus |
| `ready_state` | Bereit/Standby |
| `mic_mute` | Mikrofon stummgeschaltet |
| `reconnect_mic_state` | Verbindungsproblem Mikrofon |
| `reconnect_network_state` | Verbindungsproblem Netzwerk |

---

## Flüchtige Events auslösen (`emit_event_target`)

Events sind **kurze, einmalige Animationen** (z. B. ein Aufblitzen beim Wake-Word). Sie spielen
einmal ab und der vorherige Zustand wird danach wiederhergestellt.

```python
service.emit_event_target("wakeword_detected")
service.emit_event_target("short_flash", {"color": "0xFFFFFF"})
service.emit_event_target("warning_flash")
```

### Verfügbare Events

| ID | Beschreibung |
|---|---|
| `short_flash` | Kurzes Aufblitzen (`color`) |
| `short_pulse` | Kurzer Puls (`color`) |
| `short_ping` | Kurzes Ping (`color`) |
| `short_soft_pulse` | Kurzer weicher Puls (`color`) |
| `short_sweep` | Kurzer Sweep (`color`) |
| `short_running_dot` | Kurzer laufender Punkt (`color`) |
| `double_flash` | Doppelblitz (`color`) |
| `triple_flash` | Dreifachblitz (`color`) |
| `blink_impulse` | Blinkimpuls (`color`) |
| `sparkle_burst` | Funkenregen (`color`) |
| `warning_flash` | Warnblinken (rot) |
| — | — |
| `wakeword_detected` | Wake-Word erkannt |
| `confirm_event` | Bestätigung |
| `success_event` | Erfolg |
| `error_event` | Fehler |
| `reject_event` | Ablehnung |
| `warn_event` | Warnung |
| `notification_event` | Benachrichtigung |
| `connected_event` | Verbunden |
| `init_event` | Initialisierung |

---

## Overlays (überlagernde Anzeigen)

Overlays werden **über** dem aktiven Zustand gerendert — auf einem separaten Kanal.
Nützlich z. B. für einen Richtungsindikator oder eine Fortschrittsanzeige, die
gleichzeitig mit dem Hintergrundzustand sichtbar ist.

```python
# Richtungsanzeige setzen (DOA – Direction of Arrival)
service.set_overlay_target("direction_indicator", channel="doa", inputs={"direction": 135.0})

# Overlay aktualisieren (z. B. neue Richtung)
service.update_overlay_target("doa", {"direction": 270.0})

# Overlay entfernen
service.clear_overlay_target("doa")
```

### Verfügbare Overlays

| ID | Beschreibung |
|---|---|
| `direction_indicator` | Richtungsanzeige (DOA-Winkel) |
| `fill_ring` | Füllstandsanzeige (`fill` 0.0–1.0) |
| `progress_bar` | Fortschrittsbalken (`progress` 0.0–1.0) |
| `progress_circle` | Fortschrittskreis (`progress` 0.0–1.0) |
| `progress_ring` | Fortschrittsring |
| `highlighted_segment` | Segment hervorheben |
| `opposing_markers` | Zwei gegenüberliegende Markierungen |
| `countdown_circle` | Countdown-Kreis |
| `countdown_segment` | Countdown-Segment |
| `countdown_ring` | Countdown-Ring |
| `timer_ring` | Timer-Ring |
| `timeout_segment` | Timeout-Segment |
| `loading_spinner` | Lade-Spinner |

---

## Countdown-Timer

Der Countdown-Timer ist eine integrierte Funktion für zeitgesteuerte Anzeigen
(z. B. „Bitte in 10 Sekunden sprechen"):

```python
# Countdown starten: 10 Sekunden, danach Zustand "idle"
service.start_timeout_countdown(
    total_ms=10_000,
    follow_up_state="solid_color",
    payload={"color": "0x003300"},
)

# Countdown-Restzeit aktualisieren (z. B. wenn sich die Zeit ändert)
service.update_timeout_countdown(remaining_ms=5_000)

# Countdown abbrechen
service.cancel_timeout_countdown()
```

---

## Helligkeit und Aktivierung

```python
# Helligkeit einstellen (0.0 = aus, 1.0 = volle Helligkeit)
service.set_brightness(0.5)

# LEDs komplett deaktivieren (Engine läuft weiter, keine Ausgabe)
service.set_enabled(False)

# LEDs wieder aktivieren
service.set_enabled(True)
```

---

## Richtungsanzeige (DOA)

```python
# Richtung in Grad setzen (0–359)
service.set_direction(135.0)

# Richtungsanzeige entfernen
service.clear_direction()
```

---

## Presets

Presets sind vordefinierte Effekt-Konfigurationen mit festen Parameterwerten.
Sie können direkt als Target-Namen verwendet werden:

```python
# Preset direkt nach ID aufrufen
service.set_state_target("blink_color_idle")
service.set_state_target("blink_color_focus")
service.emit_event_target("blink_impulse_alert")
```

Alle verfügbaren Presets abfragen:
```python
presets = service.list_presets_v2()
```

---

## Vollständiges Anwendungsbeispiel: STT-App

```python
from respeaker_led import ControllerService

class SpeechAssistant:
    def __init__(self):
        self._led = ControllerService(use_device=True, fps=8.0)
        self._led.start()
        self._led.set_state_target("ready_state")

    # --- Lifecycle ---

    def shutdown(self):
        self._led.stop()

    # --- Sprachassistent-Ereignisse → LED-Steuerung ---

    def on_idle(self):
        self._led.set_state_target("ready_state")

    def on_wake_word(self):
        self._led.emit_event_target("wakeword_detected")
        self._led.set_state_target("listening")

    def on_listening_timeout(self, seconds_left: int):
        # Countdown-Overlay über dem Listening-Zustand
        self._led.start_timeout_countdown(
            total_ms=seconds_left * 1000,
            follow_up_state="ready_state",
        )

    def on_speech_end(self):
        self._led.cancel_timeout_countdown()
        self._led.set_state_target("thinking")

    def on_processing(self):
        self._led.set_state_target("processing")

    def on_response_start(self):
        self._led.set_state_target("speaking")

    def on_response_end(self):
        self._led.emit_event_target("confirm_event")
        self._led.set_state_target("ready_state")

    def on_error(self):
        self._led.emit_event_target("error_event")
        self._led.set_state_target("ready_state")

    def on_mic_muted(self):
        self._led.set_state_target("mic_mute")

    def on_direction_update(self, angle_deg: float):
        # DOA-Richtungsindikator als Overlay
        self._led.set_overlay_target(
            "direction_indicator",
            channel="doa",
            inputs={"direction": angle_deg},
        )
```

---

## Status abfragen

```python
status = service.get_status()

print(status["output_mode"])          # "device" oder "console-preview"
print(status["render_loop_running"])  # True/False
print(status["fps"])                  # Render-Framerate
print(status["render_count"])         # Anzahl gerenderter Frames
print(status["usb_connection"])       # USB-Verbindungsstatus (state, connect_count, ...)
```

---

## Fehlerbehebung

**LEDs leuchten nicht nach `service.start()`:**
Prüfe `service.get_status()["usb_connection"]["state"]`. Wenn `"CONNECTING"`:
Das Gerät wurde noch nicht gefunden. Auf Windows muss der WinUSB-Treiber über
[Zadig](https://zadig.akeo.ie/) für den reSpeaker installiert sein.

**Keine Ausgabe im Entwicklungsmodus (ohne Hardware):**
`ControllerService(use_device=False)` gibt die LED-Frames als Text auf der Konsole aus.
Das ist normal und dient zur Entwicklung ohne echte Hardware.

**Import-Fehler `from respeaker_led import ControllerService`:**
Das Paket ist noch nicht als `respeaker-led` auf PyPI veröffentlicht. Direkte Nutzung
aus dem Repository: `from src import ControllerService`.
