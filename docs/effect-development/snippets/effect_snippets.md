# Kleine LEFX-V2-Bausteine

Diese Snippets werden lokal in eine Effektquelle kopiert. Sie sind keine
gemeinsame Hilfsbibliothek.

## Verstrichene Zeit

```python
elapsed = max(0.0, ctx.now - ctx.invocation.created_at)
```

Geeignet fuer alle zeitabhaengigen Renderer.

## Zyklischer Fortschritt

```python
phase = (elapsed * speed) % 1.0
```

Ein State laeuft damit ohne internen Zaehler dauerhaft weiter.

## Fortschritt eines endlichen Effekts

```python
duration_ms = ctx.invocation.requested_duration_ms or int(params["duration_ms"])
elapsed_ms = max(0.0, (ctx.now - ctx.invocation.created_at) * 1000.0)
progress = min(1.0, elapsed_ms / max(1, duration_ms))
```

Die Engine beendet das Event oder zeitgesteuerte Overlay; der Renderer meldet
kein eigenes Ende.

## Ringposition umbrechen

```python
index = raw_index % ctx.led_count
```

## Winkel auf LED abbilden

```python
index = round((direction_deg % 360.0) / 360.0 * ctx.led_count) % ctx.led_count
```

## Transparentes Overlay

```python
frame: list[int | None] = [None] * ctx.led_count
frame[index] = color
```

`None` laesst den darunterliegenden Frame unveraendert.

## Segment zeichnen

```python
for offset in range(min(length, ctx.led_count)):
    frame[(start + offset) % ctx.led_count] = color
```

## Fehlenden Messwert neutral behandeln

```python
value = ctx.inputs.get("value")
if value is None:
    return [None] * ctx.led_count
```

## Push-Lebenszeichen

Ein externes System sendet ein leeres Input-Objekt. Die Engine aktualisiert
den Empfangszeitpunkt, behaelt aber die letzten gueltigen Werte:

```powershell
python .\main.py update overlay <channel> --inputs '{}'
```

## Pull-Abfrage

```python
def sample_inputs(self, ctx: InputContext) -> dict[str, float] | None:
    value = read_local_value()
    return None if value is None else {"value": value}
```

Das Intervall steht in `InputSamplingPolicy`. Fehler und ausbleibende
Ergebnisse werden durch die engine-eigene Input-Health behandelt.

## Farbe skalieren

```python
factor = max(0.0, min(1.0, factor))
red = int(((color >> 16) & 0xFF) * factor)
green = int(((color >> 8) & 0xFF) * factor)
blue = int((color & 0xFF) * factor)
scaled = (red << 16) | (green << 8) | blue
```

Parameter werden vor `render()` validiert. Lokales Begrenzen dient nur einer
mathematisch stabilen Darstellung und ersetzt kein Schema.

## Kein Delta-Time-Hook

V2 ruft `render()` pro Frame auf, stellt aber kein `update(delta_time)` bereit.
Verwende absolute Zeitdifferenzen. Das bleibt auch bei wechselnder FPS
deterministisch.
