# Effects Engine – Entwickler-Dokumentation

Technische Referenz fuer die Architektur, Erweiterung und Interna der Effects Engine.

## Architektur

```
led_effects/effects_engine/
├── rgb.py               # RGB-Datentyp, Farbpalette, Mathematik
├── backend.py           # LedRingBackend ABC + Implementierungen
├── context.py           # EffectContext – kooperativer Stop/Sleep
├── effects.py           # 9 Basis-Effekte (ganze-Ring-Kommandos)
├── advanced_effects.py  # 6 erweiterte Effekte (per-LED-Steuerung)
├── registry.py          # EffectRegistry – Name→Effekt-Mapping
├── config_loader.py     # Dict/JSON/YAML → Effekt-Instanzen
├── controller.py        # LedRingController – Thread-safe State/Event
├── stdlib.py            # Standard-Bibliothek (26 vorgefertigte Effekte)
└── __init__.py          # Oeffentliche API (__all__)
```

## Schichtenmodell

```
Nutzercode / CLI / API
        │
        ▼
  LedRingController          Thread-sichere Fassade
        │
   ┌────┴────┐
   │         │
 State    Event             Zwei parallele Kanaele
   │         │
   ▼         ▼
 LedEffect.run(ctx)         Kooperative Schleife
        │
        ▼
 LedRingBackend              Hardware-Abstraktion
        │
   ┌────┼────┐
   │    │    │
  XVF  Rec  Dry              Implementierungen
```

## Backend-Erweiterung: set_ring_colors()

Seit Phase 10 hat `LedRingBackend` die Methode `set_ring_colors(colors: list[RGB])`.
Sie setzt jede der 12 LEDs einzeln. Die XVF-Implementierung nutzt intern:

```
LED_EFFECT 5        → Ring-Modus aktivieren
LED_RING_COLOR hex0 hex1 ... hex11  → Farben setzen
```

**Wichtig**: `LED_COUNT = 12` ist als Konstante in `backend.py` definiert und
wird von den per-LED-Effekten importiert.

## Eigene Effekte schreiben

### Basis-Effekt (ganzer Ring)

```python
from dataclasses import dataclass
from led_effects.effects_engine import LedEffect, EffectContext, RGB

@dataclass
class MyEffect(LedEffect):
    color: RGB = RGB(0, 255, 0)

    def run(self, ctx: EffectContext) -> None:
        ctx.backend.single_color(self.color)
        ctx.sleep(1.0)  # blockiert kooperativ
```

### Per-LED-Effekt

```python
from led_effects.effects_engine import LedEffect, EffectContext, LED_COUNT, Colors

@dataclass
class MyRingEffect(LedEffect):
    def run(self, ctx: EffectContext) -> None:
        while not ctx.is_stopped:
            ring = [Colors.BLACK] * LED_COUNT
            ring[0] = Colors.RED
            ctx.backend.set_ring_colors(ring)
            if not ctx.sleep(0.05):
                return
```

### Registrierung

Neue Effekte registrieren:

1. **Python**: `controller.register("my_effect", MyEffect(...))`
2. **Config-Loader**: Builder in `_EFFECT_BUILDERS` dict eintragen
3. **Stdlib**: In `build_standard_effects()` unter semantischem Namen aufnehmen

## Kooperatives Stoppen

Effekte *muessen* regelmaessig `ctx.is_stopped` pruefen oder `ctx.sleep()` nutzen.
Endlosschleifen ohne Stop-Pruefung blockieren den Controller.

Muster:

```python
def run(self, ctx: EffectContext) -> None:
    while not ctx.is_stopped:
        # ... Rendering ...
        if not ctx.sleep(0.03):  # False = gestoppt
            return
```

## Thread-Modell

- **State-Effekt**: Laeuft in eigenem Daemon-Thread (`_state_thread`)
- **Event-Effekt**: Stoppt den State-Thread, laeuft im Event-Thread, startet State danach neu
- **Locks**: Ein `threading.Lock` schuetzt State-Wechsel und Event-Ausfuehrung
- Das `stop_event` (`threading.Event`) wird gesetzt, um laufende Effekte zu beenden

## Effekt-Typen in der Config

| `type`          | Klasse                | Pflichtfelder              |
|-----------------|-----------------------|----------------------------|
| `off`           | OffEffect             | –                          |
| `static`        | StaticColorEffect     | `color`                    |
| `breath`        | BreathEffect          | `color`                    |
| `rainbow`       | RainbowEffect         | –                          |
| `blink`         | BlinkEffect           | `color`                    |
| `alternate`     | AlternateColorEffect  | `colors` (Liste)           |
| `doa`           | DoaEffect             | `base_color`, `doa_color`  |
| `fade`          | FadeEffect            | `from_color`, `to_color`   |
| `sequence`      | SequenceEffect        | `effects` (Liste)          |
| `custom_doa`    | CustomDoaEffect       | –                          |
| `timer`         | TimerCountdownEffect  | –                          |
| `progress`      | ProgressRingEffect    | –                          |
| `spinner`       | SpinnerEffect         | –                          |
| `pulse_wave`    | PulseWaveEffect       | –                          |
| `segment_meter` | SegmentMeterEffect    | –                          |

## RecordingBackend fuer Tests

```python
from led_effects.effects_engine import RecordingBackend, EffectContext
import threading

backend = RecordingBackend()
ctx = EffectContext(backend=backend, stop_event=threading.Event())

# Effekt ausfuehren...
effect.run(ctx)

# Assertions
assert backend.calls[0].method == "set_ring_colors"
ring_colors = backend.calls[0].args[0]
assert len(ring_colors) == 12
```

## Performance-Hinweise

- Per-LED-Effekte erzeugen ~25 fps (0.04s Intervall)
- Jeder Frame = ein `set_ring_colors()`-Aufruf
- `XvfHostBackend` startet pro Aufruf einen Subprocess → praxistauglich bei ~20 fps
- Fuer hoeheren Durchsatz: Batch-Modus oder Socket-Backend (zukuenftige Erweiterung)

## Testabdeckung

- 189 Tests gesamt, davon 47 fuer die erweiterten Effekte
- Alle Effekte werden gegen `RecordingBackend` getestet
- Tests pruefen: Frame-Erzeugung, Farbverteilung, kooperatives Stoppen,
  Config-Loader-Integration, Stdlib-Vollstaendigkeit

## Dateiuebersicht

| Datei                  | Zeilen | Zweck                                      |
|------------------------|--------|---------------------------------------------|
| `rgb.py`               | ~120   | RGB-Klasse, Farbpalette, `scaled()`, `blend()` |
| `backend.py`           | ~260   | ABC + 3 Implementierungen                   |
| `context.py`           | ~45    | EffectContext mit kooperativem Stop          |
| `effects.py`           | ~180   | 9 Basis-Effekte                              |
| `advanced_effects.py`  | ~340   | 6 erweiterte per-LED-Effekte                 |
| `registry.py`          | ~90    | Registry mit Gruppen-Abfragen                |
| `config_loader.py`     | ~280   | Dict/JSON/YAML Parser + 15 Builder          |
| `controller.py`        | ~130   | Thread-sicherer Controller                   |
| `stdlib.py`            | ~160   | 26 Standard-Effekte                           |
| `__init__.py`          | ~95    | Oeffentliche API                              |
