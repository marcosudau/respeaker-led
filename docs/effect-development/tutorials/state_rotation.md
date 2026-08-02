# Tutorial: rotierender State

Das fertige Paket liegt unter
`docs/examples/effects/states/example_rotation`. Es zeigt einen dauerhaft
laufenden, deckenden Grundzustand ohne internen Mutationszustand.

## 1. Quelle erzeugen

```powershell
python .\tools\effect_packager.py init-effect .\example_rotation `
  --effect-id example_rotation_state `
  --source-id tutorial-effects `
  --title "Example Rotation State" `
  --type state
```

`effect.yaml` verbindet das Paket mit der Klasse `ExampleRotationState`.
Die Klasse erbt von `BaseEffect` und besitzt genau eine `EffectDefinition`.

## 2. Vertrag definieren

Der State erlaubt nur `STATE_LAYER`, laeuft unbestimmt und verwendet
`LOOP` beziehungsweise `PERSISTENT`. Weil er animiert und gerichtet ist,
deklariert er die V2-Standardfelder `speed` und `reverse`. Das Farbmodell
`MONO` verlangt `color` und `brightness`.

`background_color` ist eine zusaetzliche, paketlokale Konfiguration. Die
Engine legt keine fachliche Bedeutung dafuer fest.

## 3. Bewegung ohne Update-Hook

```python
elapsed = max(0.0, ctx.now - ctx.invocation.created_at)
direction = -1 if params["reverse"] else 1
head = int(elapsed * float(params["speed"]) * 4.0 * direction) % ctx.led_count
```

Aus derselben Zeit entsteht immer derselbe Frame. Es gibt keinen Timer-Thread,
kein `update()` und keinen Zustand, der beim Start zurueckgesetzt werden muss.
Der Modulo-Operator macht die Bewegung zyklisch; der State kann deshalb
unbegrenzt weiterlaufen.

## 4. Frame erzeugen

Zuerst wird ein deckender Hintergrund angelegt. Danach werden ab `head` so
viele LEDs gesetzt, wie `segment_length` vorgibt. `reverse` beeinflusst
Position und Zeichenrichtung gemeinsam.

## 5. Validieren und testen

```powershell
python .\tools\effect_packager.py validate-effect-source `
  .\docs\examples\effects\states\example_rotation
```

Pruefe mindestens Startzeit, spaetere Zeit, Ringumbruch, beide Richtungen,
minimale Segmentlaenge und einen ungueltigen Parameter. Ein Schemafehler muss
vor einer Runtime-Aenderung abgewiesen werden.
