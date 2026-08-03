# Robuste Renderrezepte

## Gemeinsame Basis

```python
params = {**ctx.definition.defaults, **ctx.params}
elapsed = max(0.0, ctx.now - ctx.invocation.created_at)
```

Nutze `ctx.inputs` in den mit diesem Skill erstellten Effekten nicht.

## Vollständiger Frame

Deckend:

```python
frame: list[int | None] = [background_color] * ctx.led_count
```

Transparent:

```python
frame: list[int | None] = [None] * ctx.led_count
```

Vor Ringberechnungen bei Bedarf absichern:

```python
if ctx.led_count <= 0:
    return []
```

## Zyklische Phase

```python
period_s = BASE_PERIOD_S / max(0.01, float(params["speed"]))
phase = (elapsed / period_s) % 1.0
```

`phase` läuft wiederholt von `0.0` bis knapp unter `1.0`.

## Weicher Puls

```python
wave = 0.5 - 0.5 * math.cos(2.0 * math.pi * phase)
intensity = min_brightness + (1.0 - min_brightness) * wave
color = blend(background_color, foreground_color, intensity)
```

Die Cosinuskurve besitzt weiche Wendepunkte.

## Blinken

```python
on = phase < duty_cycle
color = foreground_color if on else background_color
```

`duty_cycle` lokal auf `0.0..1.0` begrenzen.

## Rotierende Position

Mit entworfenen LED-Schritten pro Sekunde:

```python
direction = -1 if bool(params["reverse"]) else 1
steps = int(math.floor(elapsed * BASE_STEPS_PER_SECOND * float(params["speed"])))
head = (steps * direction) % ctx.led_count
```

## Segment mit Ringumbruch

```python
length = max(1, min(int(params["segment_length"]), ctx.led_count))
for offset in range(length):
    index = (head - direction * offset) % ctx.led_count
    frame[index] = color
```

## Weicher Schweif

```python
for offset in range(tail_length + 1):
    factor = falloff ** offset
    index = (head - direction * offset) % ctx.led_count
    frame[index] = scale_color(color, factor)
```

`falloff` liegt sinnvoll zwischen `0.0` und `1.0`.

## Scannerbewegung ohne Sprung

```python
travel = max(1, ctx.led_count - 1)
triangle = 1.0 - abs(2.0 * phase - 1.0)
index = int(round(triangle * travel))
```

Die Position läuft vor und zurück.

## Fortschritt eines endlichen Effekts

```python
duration_ms = ctx.invocation.requested_duration_ms or int(params["duration_ms"])
elapsed_ms = max(0.0, elapsed * 1000.0)
progress = min(1.0, elapsed_ms / max(1, duration_ms))
```

Die Engine beendet die Instanz. `render()` liefert nur den Frame für den
aktuellen Zeitpunkt.

## Kurzer Einmalpuls

```python
intensity = math.sin(math.pi * progress)
```

Er startet dunkel, erreicht in der Mitte das Maximum und endet dunkel.

## Sweep eines endlichen Effekts

```python
last_index = max(0, ctx.led_count - 1)
index = int(round(progress * last_index))
if reverse:
    index = last_index - index
```

## Einfache lineare Interpolation zwischen Ringpositionen

Nur verwenden, wenn eine weichere Bewegung ausdrücklich gewünscht ist:

```python
position = phase * ctx.led_count
left = int(math.floor(position)) % ctx.led_count
right = (left + 1) % ctx.led_count
mix = position - math.floor(position)
frame[left] = scale_color(color, 1.0 - mix)
frame[right] = scale_color(color, mix)
```

## Determinismus

Verboten:

```python
self.position += 1
```

Verboten sind außerdem eigene Threads, Timer und zufällige Werte ohne einen
stabilen, konfigurierbaren Seed.

Bei gleicher Konfiguration, Startzeit und `ctx.now` muss derselbe Frame
entstehen.
