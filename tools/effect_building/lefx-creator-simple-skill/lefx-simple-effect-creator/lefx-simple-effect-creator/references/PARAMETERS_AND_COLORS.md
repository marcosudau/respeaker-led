# Parameter und Farben

## Grundregel

Eine Definition akzeptiert nur vorab deklarierte Felder. Unbekannte Felder
werden abgewiesen. Verwende wenige, verständliche Parameter.

## Standardfelder

| Merkmal | Feld | Typ und typische Grenze |
|---|---|---|
| Hauptfarbe | `color` | `color` |
| zweite Farbe | `secondary_color` | `color` |
| konkrete Hintergrundfarbe | `background_color` | `color` |
| Gesamthelligkeit | `brightness` | `float`, `0.0..1.0` |
| Geschwindigkeitsfaktor | `speed` | `float`, meist `0.1..10.0` |
| Drehrichtung | `reverse` | `bool` |
| Dauer | `duration_ms` | `duration_ms`, Minimum mindestens `1` |
| Segmentbreite | `segment_length` | `int`, Minimum `1` |
| minimale Pulshelligkeit | `min_brightness` | `float`, `0.0..1.0` |

`speed=1.0` bedeutet die entworfene Grundgeschwindigkeit. Es ist keine FPS.

## Farbmodelle

| `ColorModel` | Pflichtfelder |
|---|---|
| `NONE` | keine Farbfelder |
| `MONO` | `color` |
| `DUAL` | `color`, `secondary_color` |
| `PALETTE` | `colors` |
| `GRADIENT` | `gradient` |
| `RANDOM_RANGE` | `color_range`, `random_seed` |

Jede farbige Definition benötigt zusätzlich:

```python
"brightness": EffectParamDefinition(
    name="brightness",
    type="float",
    default=1.0,
    minimum=0.0,
    maximum=1.0,
    unit="ratio",
)
```

## Kanonische Werte im Renderer

Die Engine normalisiert Werte vor `render()`:

- Farbe: `#RRGGBB`
- Dauer: Millisekunden als Integer
- Bool: echtes `bool`
- Float und Integer: validierte Zahlen

Implementiere keine zweite Eingabesprache im Effekt.

Erlaubte lokale Umwandlung für die LED-Ausgabe:

```python
def _color(value: str) -> int:
    return int(value.removeprefix("#"), 16)
```

Zum Skalieren und Mischen bevorzugt:

```python
from src.core.color_math import blend, scale_color
```

Beispiele:

```python
scaled = scale_color(color, brightness)
mixed = blend(background_color, color, mix)
```

Begrenze mathematische Zwischenwerte lokal, obwohl die Eingaben validiert sind:

```python
factor = max(0.0, min(1.0, factor))
```

## `None` und Schwarz

- `None`: bei transparenter Komposition darunterliegenden Pixel erhalten.
- `0x000000`: konkreter schwarzer Pixel; darunterliegender Pixel wird verdeckt.

Diese Werte dürfen nicht verwechselt werden.

## Defaults

Jeder Wert in `EffectDefinition.defaults` muss in `parameter_schema`
deklariert sein. Halte Parameterdefault und Definitionsdefault identisch.

```python
"speed": EffectParamDefinition(..., default=1.0),
...
defaults={"speed": 1.0},
```
