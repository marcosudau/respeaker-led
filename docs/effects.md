# Effekte Verstehen Und Neue Effekte Erstellen

Diese Seite beschreibt, was ein Effekt im heutigen Service bedeutet, wie Effektdateien aufgebaut sind und wie du neue Effekte sauber in das Repo einhaengst.

## Kurzbild

Ein Effekt ist eine Python-Klasse, die:

- von `BaseEffect` erbt
- eine `EffectDefinition` als Klassenattribut besitzt
- in `render(ctx)` fuer einen Zeitpunkt einen LED-Zustand erzeugt

Der Service scannt standardmaessig den Ordner `src/led_effects/effects/` und registriert dort alle gefundenen konkreten `BaseEffect`-Klassen automatisch.

## Wo Effekte heute liegen

Die eigentlichen Effektmodule liegen in:

- `src/led_effects/effects/`

Aktuelle Hilfsdateien dort sind zum Beispiel:

- `src/led_effects/effects/common.py`
- `src/led_effects/effects/basic.py`
- `src/led_effects/effects/overlays.py`
- `src/led_effects/effects/compatibility.py`

Wichtig:

- `src/` enthaelt die Engine, Runtime und Registry
- `src/led_effects/effects/` enthaelt die konkreten Effektimplementierungen
- `src/led_effects/preset_packs/` enthaelt optionale Preset-Bausteine oberhalb einzelner Effekte

## Wie der Service Effekte laedt

Beim Aufbau der Default-Registry passiert folgendes:

1. `build_default_effect_registry()` erzeugt eine leere Registry.
2. Die Registry registriert den Bibliotheksordner `src/led_effects/effects/` als Default-Quelle.
3. Alle Python-Dateien dort werden gescannt.
4. Jede konkrete `BaseEffect`-Unterklasse wird validiert und unter ihrer `id` registriert.

Konsequenzen:

- neue Effektdatei anlegen reicht grundsaetzlich aus
- doppelte Effekt-IDs verhindern den Start oder Reload klar und frueh
- nach Aenderungen am Effektcode solltest du den Service neu starten

## Aus welchen Bausteinen ein Effekt besteht

Jeder Effekt besteht aus zwei Haelften:

### 1. Metadaten in `definition`

Die `EffectDefinition` beschreibt:

- `id`
- `title`
- `description`
- `parameter_schema`
- `defaults`
- `layer_rules`
- `capabilities`
- `tags`

Diese Informationen sieht man indirekt auch ueber:

```powershell
python .\main.py list-effects
```

### 2. Renderlogik in `render(ctx)`

`render(ctx)` bekommt einen `RenderContext` und gibt eine Liste fuer alle LEDs zurueck.

Wichtig dabei:

- `ctx.now` ist der aktuelle Zeitpunkt
- `ctx.led_count` ist die Ringgroesse
- `ctx.layer_id` ist der Ziel-Layer
- `ctx.definition` ist die Effektdefinition
- `ctx.invocation` ist die aktuelle Invocation
- `ctx.params` sind die zur Laufzeit uebergebenen Parameter

Rueckgabewerte:

- `int` bedeutet konkrete Farbe fuer diese LED
- `None` bedeutet transparent auf dieser LED

## Wichtige Definitionsteile im Detail

### `id`

- muss eindeutig sein
- muss `snake_case` sein
- sollte stabil bleiben, weil CLI, API und Presets diese ID verwenden

### `parameter_schema`

Hier beschreibst du die erwarteten Eingaben, zum Beispiel Farben, Floats oder Dauern.

Der Service nutzt diese Informationen fuer:

- Dokumentation
- `list-effects`
- Validierungsnahe Beschreibung der Effekte

### `defaults`

Hier liegen die Default-Werte, die verwendet werden, wenn beim Setzen eines Effekts ein Parameter fehlt.

### `layer_rules`

Hier definierst du, auf welchen Layern ein Effekt erlaubt ist und welche Laufzeitregeln gelten.

Typische Punkte sind:

- erlaubte Layer
- erlaubte Playback-Modi
- endliche oder unendliche Dauer
- Transparenz
- Queue-Verhalten fuer Event-Layer

### `capabilities`

Hier beschreibst du generelle Eigenschaften des Effekts, zum Beispiel:

- ob er geloopt werden darf
- ob er transparent sein kann
- ob Queueing unterstuetzt wird
- ob er sich fuer Restores eignet

## Beispiel: minimaler Effekt

Die kleinste sinnvolle Form ist eine einzelne Python-Datei unter `src/led_effects/effects/`.

```python
from __future__ import annotations

from src.core.effect_schema import BaseEffect, EffectCapabilities, EffectDefinition, LayerId, LayerRule, PlaybackMode, RenderContext


class WarmWhiteEffect(BaseEffect):
    definition = EffectDefinition(
        id="warm_white",
        title="Warm White",
        description="Faerbt den ganzen Ring warmweiss.",
        defaults={},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules={
            LayerId.MAIN_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            ),
        },
        tags=("custom", "solid"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        return [0xFFD8B0] * ctx.led_count
```

## Beispiel: Effekt mit Parametern

```python
from __future__ import annotations

from src.core.effect_schema import (
    BaseEffect,
    EffectCapabilities,
    EffectDefinition,
    EffectParamDefinition,
    LayerId,
    LayerRule,
    PlaybackMode,
    RenderContext,
)

from src.led_effects.effects.common import _merge_params, _parse_color


class AccentFillEffect(BaseEffect):
    definition = EffectDefinition(
        id="accent_fill",
        title="Accent Fill",
        description="Faerbt den Ring in einer frei gesetzten Farbe.",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
        },
        defaults={"color": "#33AAFF"},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules={
            LayerId.MAIN_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            ),
        },
        tags=("custom", "solid"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        params = _merge_params(ctx)
        color = _parse_color(params.get("color"), 0x33AAFF)
        return [color] * ctx.led_count
```

## Anleitung: neuen Effekt anlegen

### 1. Datei im richtigen Ordner anlegen

Lege eine neue Python-Datei unter `src/led_effects/effects/` an, zum Beispiel:

- `src/led_effects/effects/accent_fill.py`

### 2. `BaseEffect` erweitern

- erbe von `BaseEffect`
- lege `definition` an
- implementiere `render(ctx)`

### 3. Parameter und Layerregeln sauber setzen

- verwende eine eindeutige `id`
- beschreibe Parameter im `parameter_schema`
- setze sinnvolle `defaults`
- gib nur die Layer frei, die wirklich passen

### 4. Service neu starten

Der aktuelle Default-Pfad wird beim Start geladen. Fuer neue oder geaenderte Effekte ist deshalb der einfachste Weg:

```powershell
python .\main.py shutdown
python .\main.py --no-device serve --host 127.0.0.1 --port 8765
```

### 5. Effekt pruefen

Zuerst kontrollieren, ob die ID sichtbar ist:

```powershell
python .\main.py list-effects
```

Dann den Effekt anwenden:

```powershell
python .\main.py apply-effect accent_fill main --params '{"color":"0xFF6699"}'
```

### 6. Optional Tests ergaenzen

Empfohlen ist mindestens:

- ein Test fuer `render(ctx)`
- ein Test fuer Parameterdefaults oder Grenzwerte
- optional ein Test, dass der Effekt auf den vorgesehenen Layern funktioniert

Der Standardlauf ist:

```powershell
pytest -q --basetemp=.pytest_tmp
```

## Praktische Regeln fuer austauschbare Effekte

- keine doppelten IDs verwenden
- Effekte klein und thematisch pro Datei oder Dateigruppe halten
- gemeinsam genutzte Helfer in `src/led_effects/effects/common.py` auslagern
- Engine-Code in `src/` nicht mit konkreter Effektlogik vermischen
- fuer projektinterne Module nach Moeglichkeit absolute Imports verwenden

## Wie Effekte ausgetauscht werden koennen

Der neue Aufbau erlaubt zwei typische Austauschwege:

### Vorhandenen Effekt weiterentwickeln

- bestehende Datei unter `src/led_effects/effects/` anpassen
- gleiche `id` behalten
- Service neu starten

### Neuen Effekt neben bestehende setzen

- neue Datei mit neuer `id` anlegen
- Service neu starten
- ueber `list-effects` und `apply-effect` verwenden

Wichtig:

- parallele doppelte IDs sind nicht erlaubt
- ein oeffentlicher Runtime-Reload per CLI oder API existiert aktuell nicht

## Beziehung zu Presets

Ein einzelner Effekt ist die technische Basiseinheit.

Ein Preset ist eine hoehere Schicht, die:

- einen oder mehrere Effekte kombiniert
- Payload und Modus vorbelegt
- als wiederverwendbarer Einstiegspunkt fuer CLI oder API dient

Wenn du nur eine neue Visualisierung brauchst, beginne fast immer mit einem Effekt unter `src/led_effects/effects/`.
Wenn du daraus spaeter einen wiederverwendbaren Workflow machen willst, baue darauf ein Preset-Pack.

## Weiterfuehrende Seiten

- [Schnellstart](getting_started.md)
- [CLI und API](api_guide.md)
- [Aktueller Ansatz im Repo](current_approach.md)
- [Preset-Packs](presets.md)
- [Entwickler-Einstiege](dev/index.md)