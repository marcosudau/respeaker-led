# Hier anfangen

Wenn du einfach nur mal kurz bunte LEDs sehen willst, brauchst du am Anfang **weder API noch Presets noch Dev-Doku**.

## Der einfachste Weg

```python
from led_effects.effects_engine import easy_hardware

ring = easy_hardware()
ring.color("blue")
```

Wenn du danach wieder ausschalten willst:

```python
ring.off()
```

## Was du am Anfang ignorieren kannst

Diese Dinge sind fuer den ersten Start nicht noetig:

- `docs/dev/`
- `src/`-Interna
- Preset-Packs
- die REST-API
- JSON/YAML-Konfigurationen

## Die drei typischen Wege

### 1. Ich will einfach nur etwas anzeigen

Dann lies:

- [LEDs in 2 Minuten anzeigen](effects_engine_2_minuten.md)

### 2. Ich will eigene Anzeigen als Datei definieren

Dann lies:

- [Eigene Anzeigen Schritt fuer Schritt](effects_engine_tutorial.md)

Wichtig dabei:

- JSON/YAML werden lokal in Python geladen
- JSON/YAML werden nicht an die API geschickt

### 3. Ich will einen laufenden Controller fernsteuern

Dann lies:

- [CLI und API](api_guide.md)

Das ist ein anderer Weg als die lokale Effects Engine.

## Das mentale Modell in einem Satz

- **Easy API / Python**: direkt Licht anzeigen
- **JSON/YAML**: eigene lokale Effektdefinitionen laden
- **CLI/API**: laufenden Service fernsteuern

## Gute naechste Schritte

- [LEDs in 2 Minuten anzeigen](effects_engine_2_minuten.md)
- [Wegweiser durchs Repo](layers.md)
- [Welche Anzeigen es gibt](effects_engine.md)
