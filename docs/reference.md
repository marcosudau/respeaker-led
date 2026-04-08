# Referenz

Diese Seite ist die kompakte Nachschlageversion fuer Nutzer.

Wenn du ganz neu bist, beginne vorher mit:

- [Hier anfangen](getting_started.md)
- [LEDs in 2 Minuten anzeigen](effects_engine_2_minuten.md)

## Wofuer Welche Schnittstelle Da Ist

### Easy API

Nutzen, wenn du lokal und direkt etwas anzeigen willst.

### JSON/YAML

Nutzen, wenn du feste Effektdefinitionen in Dateien haben willst.

### CLI/API

Nutzen, wenn du einen laufenden Controller-Service fernsteuern willst.

Wichtig:

- JSON/YAML werden lokal geladen
- JSON/YAML werden nicht an die API geschickt

## Easy API

Einfachster Start:

```python
from led_effects.effects_engine import easy_hardware

ring = easy_hardware()
ring.color("blue")
```

### Wichtigste Methoden

| Methode | Zweck |
|---|---|
| `show(name)` | vorhandenen Standardnamen anzeigen |
| `color(color, seconds=None)` | feste Farbe |
| `blink(color, times=2)` | kurze Rueckmeldung |
| `breathe(...)` | atmende Anzeige |
| `rainbow(...)` | Regenbogen |
| `spinner(..., seconds=None)` | Aktivitaetsanzeige |
| `pulse_wave(..., seconds=None)` | bewegte Welle |
| `timer(seconds)` | Countdown |
| `progress(value)` | Fortschrittsanzeige |
| `pointer(degrees)` | Richtungszeiger |
| `meter(value)` | Pegelanzeige |
| `choices()` | vorhandene einfache Namen |
| `off()` / `stop()` | ausschalten |

## Farben

Farben koennen in mehreren Formaten angegeben werden:

- Name: `"blue"`, `"cyan"`, `"soft_green"`
- Hex: `"#00FFCC"`, `"0x00FFCC"`
- RGB-Liste oder Tupel: `[255, 120, 0]`

## Config-Typen fuer JSON/YAML

Alle aktuell unterstuetzten `type`-Werte:

- `off`
- `static`
- `breath`
- `rainbow`
- `blink`
- `alternate`
- `doa`
- `fade`
- `sequence`
- `custom_doa`
- `timer`
- `progress`
- `spinner`
- `pulse_wave`
- `segment_meter`

## Was in JSON/YAML geht

- Zahlen
- Strings
- Farben
- Booleans
- Listen
- verschachtelte `sequence`-Effekte

## Was in JSON/YAML nicht geht

Diese Dinge brauchen Python und koennen nicht direkt aus JSON/YAML kommen:

- `direction_provider`
- `progress_provider`
- `level_provider`

## Standardnamen

### States

- `state_idle`
- `state_waiting`
- `state_processing`
- `state_connecting`
- `state_offline`
- `state_muted`
- `state_listening`
- `state_thinking`
- `state_speaking`
- `state_doa`
- `state_spinner`
- `state_dual_spinner`
- `state_pulse_wave`
- `state_custom_doa`

### Events

- `event_success`
- `event_warning`
- `event_error`
- `event_notification`
- `event_connected`
- `event_disconnected`
- `event_ack`
- `event_timer_10s`
- `event_timer_30s`
- `event_timer_60s`

### System

- `system_boot`
- `system_shutdown`

## Komplettbeispiele

- JSON: [examples/effects_full.json](examples/effects_full.json)
- YAML: [examples/effects_full.yaml](examples/effects_full.yaml)

## CLI Kurzuebersicht

Wichtige Befehle:

- `serve`
- `ping`
- `status`
- `set-state`
- `emit-event`
- `start-countdown`
- `set-direction`
- `list-presets`

Mehr dazu: [api_guide.md](api_guide.md)

## Wenn du Klassen und Interna suchst

Das ist jetzt bewusst aus der Nutzer-Referenz herausgezogen.

Dafuer gibt es:

- [dev/effects_engine_dev.md](dev/effects_engine_dev.md)
- [dev/public_entry_points.md](dev/public_entry_points.md)
