# Parameter und Werte

V2 ist an der Eingabegrenze fehlertolerant, intern aber strikt. Eine
Definition legt alle akzeptierten Felder und Wertebereiche vorab fest.

## Konfiguration aufloesen

```text
Definition-Defaults
-> optionales Preset
-> explizite Werte des Steuerungskommandos
-> Validierung und Kanonisierung
```

Explizite Werte haben Vorrang. Ein Preset ist nur ein optionaler Ausgangspunkt.
Unbekannte Felder werden nicht still ignoriert.

## Standardparameter

Standardnamen gelten nur, wenn das entsprechende Merkmal vorhanden ist:

| Merkmal | Feld | Semantik |
|---|---|---|
| farbig | `brightness` | Helligkeitsfaktor `0.0` bis `1.0` |
| animiert | `speed` | Multiplikator der entworfenen Grundgeschwindigkeit |
| gerichtet | `reverse` | Bewegungsrichtung umkehren |
| Winkel | `direction_deg` | Winkel in Grad |
| Fortschritt | `progress` | Wert von `0.0` bis `100.0` |
| endlich | `duration_ms` oder `total_ms` | Dauer in Millisekunden |

`speed` ist keine FPS-Angabe. Die Engine darf mit einer anderen Framerate
rendern, ohne dass sich die zeitbezogene Bedeutung von `speed=1.0` aendert.

Weitere wiederkehrende Namen:

| Feld | Semantik |
|---|---|
| `color` | Haupt- beziehungsweise Vordergrundfarbe |
| `secondary_color` | zweite gleichwertige Farbe im Dual-Modell |
| `background_color` | Hintergrundfarbe der konkreten Darstellung |
| `colors` | geordnete Palette |
| `gradient` | geordnete Farbstopps |
| `color_range` | HSV-Bereich fuer reproduzierbare Zufallsauswahl |
| `random_seed` | Seed fuer dieselbe zufaellige Folge |
| `min_brightness` | optionaler unterer Helligkeitswert |

`background_color` ist ein normaler Paketparameter. Er ist nicht der
Background State des Layer-Systems.

## Unterstuetzte Wertetypen

| Typ | Kanonischer Wert | Akzeptierte Eingaben |
|---|---|---|
| `bool` | Boolean | Boolean, `0`/`1`, englische und deutsche Schalter |
| `int` | Integer | Ganzzahl oder konvertierbarer Zahlenwert |
| `float` | Float | Zahl; bei passenden Grenzen auch Prozentnotation |
| `duration_ms` | Integer Millisekunden | Zahl, `1500ms`, `1.5s` |
| `angle_deg` | Float `0 <= x < 360` | Zahl, `90deg`, `90°` |
| `enum` | deklarierter Enum-Wert | exakter Wert, Strings ohne Beachtung der Grossschreibung |
| `color` | `#RRGGBB` | Name, Hexstring oder RGB-Integer |
| `color_list` | Liste aus `#RRGGBB` | Liste aus Farbeingaben |
| `gradient` | Liste kanonischer Stops | 2 bis 16 `{at,color}`-Objekte |
| `color_range` | HSV-Bereich | Objekt mit Hue, Saturation und Brightness |

## Farbmodelle

### Mono

```json
{"color":"#33AAFF","brightness":0.8}
```

### Dual

```json
{"color":"#FFFFFF","secondary_color":"#111111","brightness":1.0}
```

### Palette

```json
{"colors":["red","orange","yellow"],"brightness":0.9}
```

### Gradient

```json
{
  "gradient": [
    {"at":0.0,"color":"red"},
    {"at":0.5,"color":"orange"},
    {"at":1.0,"color":"yellow"}
  ],
  "brightness":1.0
}
```

Gradienten sind geordnet und enthalten einen Start bei `0.0` sowie ein Ende
bei `1.0`.

### Zufallsbereich

`random_range` verwendet einen begrenzten HSV-Bereich und `random_seed`.
Der Seed macht dieselbe Konfiguration reproduzierbar.

## Freundliche Eingabeformen

Systemgrenzen akzeptieren dokumentierte, eindeutige Formen:

| Eingabe | Kanonischer Wert |
|---|---|
| `blue`, `blau`, `#0000FF`, `0x0000FF` | `#0000FF` |
| `1.5s`, `1500ms` | `1500` |
| `50%` bei Ratio `0..1` | `0.5` |
| `50%` bei Prozent `0..100` | `50.0` |
| `90deg`, `90` | `90.0` |
| `on`, `an`, `ja`, `true` | `true` |

Gross-/Kleinschreibung und umgebende Leerzeichen duerfen normalisiert werden.
Mehrdeutige oder unbekannte Werte werden abgewiesen.

Die vollstaendige Farbliste gehoert zur Wertreferenz der Implementierung und
wird hier zentral aufgefuehrt.

## Farbnamen und Aliase

| Kanonischer Name | Hex | Akzeptierte Aliase |
|---|---|---|
| `black` | `#000000` | `schwarz` |
| `white` | `#FFFFFF` | `weiss`, `weiß` |
| `red` | `#FF0000` | `rot` |
| `green` | `#00FF00` | `gruen`, `grün` |
| `blue` | `#0000FF` | `blau` |
| `cyan` | `#00FFFF` | `tuerkis`, `türkis` |
| `yellow` | `#FFFF00` | `gelb` |
| `orange` | `#FF8000` | - |
| `purple` | `#8000FF` | `lila`, `violett`, `violet` |
| `pink` | `#FF1493` | `rosa` |

Zusaetzlich akzeptiert `color`:

- `#RRGGBB`
- `0xRRGGBB`
- RGB-Integer von `0` bis `0xFFFFFF`

Ausgegeben und intern an Renderer uebergeben wird immer `#RRGGBB` in
Grossbuchstaben.

## Detaillierte strukturierte Werte

### Gradient

Ein Gradient:

- besitzt 2 bis 16 Stops,
- jeder Stop enthaelt exakt `at` und `color`,
- ist nach `at` sortiert,
- beginnt bei `0.0`,
- endet bei `1.0`.

```json
[
  {"at": 0.0, "color": "#FF0000"},
  {"at": 0.5, "color": "#FF8000"},
  {"at": 1.0, "color": "#FFFF00"}
]
```

### Color Range

```json
{
  "hue": [180.0, 260.0],
  "saturation": [0.6, 1.0],
  "brightness": [0.3, 0.9]
}
```

Das Objekt enthaelt exakt diese drei Felder. Grenzen:

- `hue`: `0.0` bis `360.0`
- `saturation`: `0.0` bis `1.0`
- `brightness`: `0.0` bis `1.0`

Jedes Wertepaar muss aufsteigend sein.

### Boolean

Wahre Eingaben:

```text
true, 1, "1", "true", "yes", "on", "ja", "an"
```

Falsche Eingaben:

```text
false, 0, "0", "false", "no", "off", "nein", "aus"
```

Diese Wertnormalisierung ist umfangreicher als die Boolean-Syntax einzelner
CLI-Optionsflags. Die Unterschiede sind in der
[CLI-Referenz](../cli_guide.md) aufgefuehrt.

## Aliase

Eine Definition darf fuer ein kanonisches Feld explizite Aliase deklarieren.
Sie gelten nur an der Validierungsgrenze.

```text
Eingabe:  direction
Intern:   direction_deg
```

Kanonischer Name und Alias duerfen nicht gleichzeitig gesendet werden.
Aliase duerfen weder mit anderen Feldern noch untereinander kollidieren.

## Grenzen und Fehler

Nach der Normalisierung werden Minimum, Maximum, Enum-Werte, Nullbarkeit und
Pflichtstatus geprueft. Fehler enthalten:

- Fehlercode
- konkreten Feldpfad
- abgewiesenen Wert
- lesbare Meldung
- gegebenenfalls Vorschlaege

Ein Renderer erhaelt kanonische, validierte Werte. Er soll keine zweite
Eingabesprache, Farbaliasliste oder Dauerparser implementieren. Lokales
Begrenzen mathematischer Zwischenergebnisse bleibt erlaubt.
