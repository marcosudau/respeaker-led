# Effects Engine in 2 Minuten

Das ist der einfachste Einstieg.

Wenn du nur willst, dass der Ring etwas zeigt, brauchst du genau das hier:

```python
from led_effects.effects_engine import easy_hardware

ring = easy_hardware()
ring.color("blue")
```

Fertig.

## Die 3 wichtigsten Zeilen

```python
from led_effects.effects_engine import easy_hardware

ring = easy_hardware()
ring.off()
```

- `easy_hardware()` verbindet sich mit `python_control/xvf_host.py`
- `ring` ist dein einfaches Bedienobjekt
- `ring.off()` schaltet alles aus

## Die einfachsten Befehle

### Feste Farbe

```python
ring.color("blue")
ring.color("red")
ring.color("#00FFCC")
ring.color([255, 120, 0])
```

### Fertige Standard-Effekte

```python
ring.show("idle")
ring.show("listening")
ring.show("processing")
ring.show("spinner")
```

### Kurze Rueckmeldungen

```python
ring.show("success")
ring.show("warning")
ring.show("error")
```

### Eigene schnelle Helfer

```python
ring.blink("yellow", times=3)
ring.breathe("cyan")
ring.rainbow()
```

## Wenn ein Effekt nur kurz laufen soll

```python
ring.spinner(seconds=5)
ring.pulse_wave(seconds=4)
ring.color("green", seconds=2)
```

Das ist absichtlich so gebaut, damit du kein Threading und keine Stop-Logik lernen musst.

## Die coolen Sachen

### Countdown

```python
ring.timer(10)
```

### Fortschritt

```python
ring.progress(0.25)
ring.progress(0.50)
ring.progress(0.90)
```

### Richtungszeiger

```python
ring.pointer(45)
ring.pointer(180)
```

### Pegelanzeige

```python
ring.meter(0.2)
ring.meter(0.8)
```

## Was kann ich alles anzeigen?

```python
print(ring.choices())
```

Das gibt dir einfache Namen ohne Prefixe, zum Beispiel:

- `idle`
- `listening`
- `spinner`
- `success`
- `warning`
- `boot`

## Ohne Hardware testen

```python
from led_effects.effects_engine import easy_preview

ring = easy_preview()
ring.color("blue")
ring.spinner(seconds=3)
```

`easy_preview()` schickt keine Befehle an die Hardware, sondern loggt nur mit.

## Komplettbeispiel

```python
from led_effects.effects_engine import easy_hardware

ring = easy_hardware()

ring.color("blue", seconds=1)
ring.blink("yellow", times=2)
ring.spinner(seconds=3)
ring.timer(5)
ring.show("success")
ring.off()
```

## Wenn du mehr willst

- Praktisches Tutorial: [effects_engine_tutorial.md](effects_engine_tutorial.md)
- Volle Engine-Doku: [effects_engine.md](effects_engine.md)
- Vollstaendige JSON-Beispiele: [examples/effects_full.json](examples/effects_full.json)
- Vollstaendige YAML-Beispiele: [examples/effects_full.yaml](examples/effects_full.yaml)