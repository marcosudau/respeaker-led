# Effekte Verstehen Und Neue Effekte Erstellen

Diese Seite beschreibt, was ein Effekt im heutigen Service bedeutet, wie Effektdateien aufgebaut sind und wie du neue Effekte sauber in das Repo einhaengst.

## Kurzbild

Ein Effekt ist eine Python-Klasse, die:

- von `BaseEffect` erbt
- eine `EffectDefinition` als Klassenattribut besitzt
- in `render(ctx)` fuer einen Zeitpunkt einen LED-Zustand erzeugt

Die Python-Klassen sind die Buildquellen. Der Service registriert Standardeffekte nicht direkt aus diesen Dateien, sondern aus gebauten `.lefx`- und `.lefxset`-Artefakten.

## Wo Effekte heute liegen

Die Buildquellen fuer die Standardeffekte liegen in:

- `src/led_effects/effects/basic.py`
- `src/led_effects/effects/overlays.py`
- `src/led_effects/effects/ring_effects.py`
- `src/led_effects/effects/common.py`

Das veroeffentlichte Standard-Artefakt liegt in:

- `src/led_effects/effects/default-effects.lefxset`

Optional zusaetzliche Laufzeit-Artefakte liegen in:

- `src/led_effects/packages/`
- `packages/` neben der EXE im Release-Bundle

Wichtig:

- `src/` enthaelt Engine, Runtime, Registry und Packaging
- `src/led_effects/effects/` enthaelt die Python-Buildquellen fuer die Standardeffekte
- `src/led_effects/effects/default-effects.lefxset` ist die Default-Bibliothek fuer Entwicklung und Packaging
- `src/led_effects/packages/` enthaelt optionale zusaetzliche Effektartefakte

## Wie der Service Effekte laedt

Beim Aufbau der Default-Registry passiert folgendes:

1. `build_default_effect_registry()` erzeugt eine leere Registry.
2. Die Runtime sucht zuerst nach `effects/default-effects.lefxset` neben der EXE.
3. Falls dort kein Bundle-Artefakt liegt, wird in der Entwicklungsumgebung `src/led_effects/effects/default-effects.lefxset` verwendet.
4. Das Effektset wird als Quelle `default-effects` geladen.
5. Zusaetzliche `.lefx`- und `.lefxset`-Artefakte koennen aus `packages/` autodiscovered oder ueber CLI/API registriert werden.

Konsequenzen:

- neue Python-Datei alleine reicht nicht aus; sie muss in den Buildpfad aufgenommen und gebaut werden
- doppelte Effekt-IDs verhindern Build, Start oder Reload klar und frueh
- nach Aenderungen am Effektcode solltest du `python tools/effect_building/build_lefxset.py --rebuild-packages` ausfuehren und danach den Service neu starten oder `reload-effect-sources` verwenden

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

- bestehende Buildquelle unter `src/led_effects/effects/` anpassen
- `python tools/effect_building/build_lefxset.py --rebuild-packages` ausfuehren
- gleiche `id` behalten
- Service neu starten oder `reload-effect-sources` ausfuehren

### Neuen Effekt neben bestehende setzen

- neue Effektklasse mit neuer `id` anlegen
- falls sie in einem neuen Modul liegt, das Modul in `tools/effect_building/standard_effects.py` in `_MODULE_BUNDLES` aufnehmen
- `python tools/effect_building/build_lefxset.py --rebuild-packages` ausfuehren
- Service neu starten oder `reload-effect-sources` ausfuehren
- ueber `list-effects` und `apply-effect` verwenden

Wichtig:

- parallele doppelte IDs sind nicht erlaubt
- Rohquellpfade koennen nicht mehr als Effektquelle registriert werden
- ein oeffentlicher Reload fuer Artefaktquellen existiert ueber `reload-effect-sources`

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
- [Effekt-Presets und Commands](presets.md)
- [Entwickler-Einstiege](dev/index.md)