# Eigene Anzeigen Schritt Fuer Schritt

Diese Seite fuehrt einmal sauber durch die normalen Nutzerfragen.

Nicht nach internen Klassen.
Nicht nach Architektur.
Sondern nach dem echten Arbeitsablauf.

## Schritt 1: Erstmal etwas sichtbar machen

Wenn du einfach nur Licht sehen willst:

```python
from led_effects.effects_engine import easy_hardware

ring = easy_hardware()
ring.color("blue")
```

Wenn du keine Hardware testen willst:

```python
from led_effects.effects_engine import easy_preview

ring = easy_preview()
ring.color("blue")
```

## Schritt 2: Verstehen, was du eigentlich ausloest

Es gibt im Alltag zwei Sorten Anzeigen:

- **State**: bleibt an, bis du etwas anderes setzt
- **Event**: spielt kurz und ist wieder weg

Beispiele:

- `idle`, `listening`, `spinner` sind typische States
- `success`, `warning`, `error` sind typische Events

Mit der einfachen API kannst du beides direkt benutzen:

```python
ring.show("idle")
ring.show("success")
```

## Schritt 3: Entscheiden, ob du Python oder JSON/YAML brauchst

### Nimm Python, wenn

- du sofort etwas anzeigen willst
- du Live-Werte hast
- du kleine Skripte schreiben willst

### Nimm JSON/YAML, wenn

- du feste Effektdefinitionen als Datei pflegen willst
- du wiederverwendbare Effektsets bauen willst
- du keine neue Python-Klasse schreiben willst

## Schritt 4: Verstehen, was JSON/YAML im Repo sind

JSON/YAML-Dateien sind **lokale Effektdefinitionen**.

Sie werden in Python geladen.

Zum Beispiel so:

```python
from led_effects.effects_engine import (
    LedRingController,
    XvfHostBackend,
    load_effects_from_json,
)

backend = XvfHostBackend("python_control/xvf_host.py")
effects = load_effects_from_json("docs/examples/effects_full.json")
controller = LedRingController(backend, effects)

controller.set_state("static_blue")
```

Wichtig:

- JSON/YAML werden nicht an die API geschickt
- JSON/YAML sind keine HTTP-Payload fuer den Controller-Service

## Schritt 5: Eigene Effekte aus JSON laden

Minimalbeispiel:

```json
{
  "mein_blau": {
    "type": "static",
    "color": "blue",
    "persistent": true
  }
}
```

Laden:

```python
from led_effects.effects_engine import load_effects_from_json

effects = load_effects_from_json("meine_effekte.json")
```

## Schritt 6: Eigene Effekte aus YAML laden

Minimalbeispiel:

```yaml
mein_blau:
  type: static
  color: blue
  persistent: true
```

Laden:

```python
from led_effects.effects_engine import load_effects_from_yaml

effects = load_effects_from_yaml("meine_effekte.yaml")
```

## Schritt 7: Wissen, was per Config geht und was nicht

Per JSON/YAML gehen feste Werte wie:

- Farben
- Zahlen
- Booleans
- Wiederholungen
- Sequenzen aus mehreren Effekten

Nicht per JSON/YAML gehen Python-Callbacks wie:

- `direction_provider`
- `progress_provider`
- `level_provider`

Wenn du echte Live-Werte anzeigen willst, brauchst du Python.

## Schritt 8: Typische Faelle

### Feste Anzeige

```python
ring.color("green")
```

### Kurze Rueckmeldung

```python
ring.show("success")
ring.blink("yellow", times=2)
```

### Laufende Aktivitaet

```python
ring.show("spinner")
ring.spinner(seconds=5)
```

### Countdown

```python
ring.timer(10)
```

### Fortschritt

```python
ring.progress(0.65)
```

### Richtung

```python
ring.pointer(180)
```

## Schritt 9: Komplette Vorlagen nutzen

Vollstaendige Beispiel-Dateien liegen hier:

- JSON: [examples/effects_full.json](examples/effects_full.json)
- YAML: [examples/effects_full.yaml](examples/effects_full.yaml)

Diese Dateien decken alle aktuell per Config unterstuetzten Typen ab.

## Schritt 10: Wann brauchst du die API?

Nur dann, wenn du einen bereits laufenden Controller-Prozess fernsteuern willst.

Also zum Beispiel fuer:

- lokale REST-Steuerung
- externe Tools
- Automatisierung ueber Prozesse

Wenn du nur lokal Effekte definieren und anzeigen willst, brauchst du die API nicht.

## Wenn du an einer Stelle haengst

Die normale Reihenfolge ist jetzt:

1. [LEDs in 2 Minuten anzeigen](effects_engine_2_minuten.md)
2. diese Tutorial-Seite
3. [Farben, Typen und Namen zum Nachschlagen](reference.md)
4. erst danach [CLI und API](api_guide.md) oder [Entwickler-Doku](dev/index.md)
