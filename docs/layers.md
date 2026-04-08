# Wegweiser Durchs Repo

Diese Seite ist der Orientierungsplan fuer das Repo.

Wenn du bisher das Gefuehl hattest, dass alles durcheinander ist, dann ist das der richtige Einstieg.

## Was die meisten Leute eigentlich wollen

Meistens geht es um genau eine dieser vier Fragen:

1. **Ich will einfach LEDs anzeigen**
2. **Ich will eigene Effekte als Datei definieren**
3. **Ich will einen laufenden Controller fernsteuern**
4. **Ich will intern am System entwickeln**

Abhaengig davon brauchst du unterschiedliche Ordner.

## Die wichtigsten Ordner

### `docs/`

Die normale Benutzer-Doku.

Hier solltest du anfangen, wenn du LEDs anzeigen oder das Projekt benutzen willst.

### `docs/dev/`

Die Entwickler-Doku.

Hier liegt das, was vorher viel zu oft mitten in der normalen Doku gelandet ist:

- Architektur
- interne Layer
- oeffentliche Einstiegspunkte
- technische Details der Effects Engine

Wenn du nicht am Code arbeitest, kannst du diesen Ordner erstmal ignorieren.

### `led_effects/effects_engine/`

Das ist **Framework-Code**, nicht einfach nur eine Sammlung von Effektdateien.

Hier liegt die eigentliche Effects Engine:

- Effektklassen
- Controller
- Backend
- Loader fuer JSON/YAML
- einfache API fuer direkte Nutzung

Wenn du nur Effekte **benutzen** willst, musst du hier normalerweise nicht Datei fuer Datei lesen.

### `led_effects/preset_packs/`

Hier liegen optionale Effekt- oder Preset-Packs.

Das ist eine Erweiterungsschicht. Sie ist nicht noetig, um mit der Effects Engine oder mit JSON/YAML eigene Anzeigen zu bauen.

### `src/`

Hier liegt der lokale Controller-Prozess:

- CLI
- API
- Runtime
- Service
- Renderer

Dieser Ordner ist wichtig, wenn du ueber CLI oder API arbeiten willst.

Er ist **nicht** der erste Einstieg fuer jemanden, der nur schnell ein paar Lichter zeigen will.

### `python_control/`

Low-Level-Hardwarezugriff auf den ReSpeaker.

Das brauchst du nur, wenn du direkt mit der Hardware-Kommunikation oder dem `xvf_host.py`-Pfad zu tun hast.

### `tests/`

Tests fuer Engine, Runtime, API und Adapter.

## Die wichtigste Trennung im ganzen Projekt

### JSON/YAML

JSON/YAML-Dateien sind **lokale Effektdefinitionen**.

Sie werden aus Python geladen, zum Beispiel mit:

```python
from led_effects.effects_engine import load_effects_from_json

effects = load_effects_from_json("docs/examples/effects_full.json")
```

### API / CLI

API und CLI steuern einen **laufenden Controller-Service**.

Das ist ein anderer Weg.

JSON/YAML werden nicht per POST an die API geschickt.

Genau dieser Unterschied war bisher an mehreren Stellen zu wenig klar.

## Welcher Weg passt zu welchem Ziel?

### Ich will einfach Licht sehen

- [Hier anfangen](getting_started.md)
- [LEDs in 2 Minuten anzeigen](effects_engine_2_minuten.md)

### Ich will eigene Anzeigen als Datei bauen

- [Eigene Anzeigen Schritt fuer Schritt](effects_engine_tutorial.md)
- [Farben, Typen und Namen zum Nachschlagen](reference.md)

### Ich will den laufenden Controller fernsteuern

- [CLI und API](api_guide.md)

### Ich will intern verstehen, wie das System arbeitet

- [Entwickler-Doku](dev/index.md)

## Warum `led_effects/` mehr als nur Effektdateien enthaelt

Weil dort zwei verschiedene, aber zusammengehoerige Dinge liegen:

- die **Engine**, also der Code zum Anzeigen von Effekten
- optionale **Packs**, also Erweiterungen mit fertigen Vorlagen

Wenn man das nicht sagt, wirkt der Ordner chaotisch. Darum gibt es jetzt zusaetzliche README-Dateien direkt in den betreffenden Ordnern.

## Was du am Anfang nicht lesen musst

- `docs/dev/effects_engine_dev.md`
- `docs/dev/public_entry_points.md`
- interne Runtime-Layer
- Preset-Pack-Build-Kontrakte

Diese Themen sind fuer interne Entwicklung da, nicht fuer den ersten Nutzereinstieg.
