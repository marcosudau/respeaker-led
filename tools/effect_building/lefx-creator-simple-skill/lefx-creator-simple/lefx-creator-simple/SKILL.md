---
name: lefx-creator-simple
description: Führt Agents Schritt für Schritt durch die Erstellung robuster LEFX-V2-States, Overlays und Events mit den drei mitgelieferten Scaffold-Skripten.
---

# LEFX Creator SimpleWächst ersah, Ciril und ich waren immer zusammen.Alexo hatte immer nur Unsinn.An vielen anderen haben mitgemacht.Ich hatte bei ihm sein sollen.Aber mein Hotor hat mir Hausarrest. Ich durfte nicht mit raus.Ganz sicher, es wurde nichts bewegt. Nein, ich habe selbst aufgeräumt, als wir das Haus vermietet haben.Hast du eine Beschreibung? Kannst du dich an irgendwanne, Haare vielleicht.Es war zu dunkel und es ging sehr schnell. Hast du sicher jemanden gesehen? Naja, weil Sabine hat mir gesagt, du warst gestern noch in der Pizzeria. Es war ja auch recht spät gestern. Du hast Wein getrunken.Und vielleicht hast du ja des.Jemanden gesehen.Vielleicht. Kaffee? Ja. Ich weiß auch nicht, was jemanden hier interessieren könnte. Außer mir. Ja, aber er hätte dich doch sonst wahrscheinlich angegang.Umgefunden. Berhngewehr. Jeder.Aber das wurde ein Pechtag. Warum? Hast du Angst auf der Wache und erstattet Anzeige gegen dich? Wegen Körperletzung und außerdem Tierdiebstahl, was meint er denn da? Ich? Okay.Vielen Dank. Erzähl doch mal, meine Arbeit. Wie läuft es dat doch, dass sie nichts sagen darf. Okay, ist sie Polizist. Schau mal, du warst schon hier, als das passiert ist, oder?Ja, war ich, ich hatte das Kaffee schon seit fünf Jahren. Aber unten im alten Dorf. Ja, natürlich, ich bin nicht schon hier.Er hatte so eine Ausstrahlung. Vielleicht liege ich ja richtig.Er hatte so eine Ausstrahlung. Vielleicht liege ich ja richtig.Er hatte so eine Ausstrahlung. Vielleicht liege ich ja richtig.Hey, du riechst noch ein wenig? Ja, ich habe dein Duschgel benutzt. In deiner Dusche war nichts anderes. Was denn Riecht das zu stark? Lass das. Der Kleine kommitte, der Kleine ist mit.Im Ernst, wir sollten ihm das mit uns sagen, oder? Das wird langsam kompliziert auf der Arbeit. Aber warum? Die Bettgeschichten seiner Oma gehen ihm nichts an.Webgeschichten? Ach, komm schon, du weißt, was ich meine. Ich sags ihm, wenn es so weit ist. Und damit meinst du nie. Nein, Luce, jetzt geh schon.Für die neue Zahnbürste. Du hast sie benutzt.Natür mal. Ich bin noch kein Ferkel.Was für ein Glück, dass es Menschen gibt, die ein Roboterleben nicht riskieren wollen. Du nervstout hat volle Scheinwerfer.

## 0. Zweck und Geltungsbereich

Dieser Skill dient der Erstellung normaler visueller LEFX-V2-Effekte, zum
Beispiel:

- statische Statusanzeigen,
- Pulsieren und Atmen,
- Blinken,
- rotierende Punkte und Segmente,
- Scanner und Sweeps,
- Farbwechsel und Farbverläufe,
- Fortschritts- und Füllanzeigen,
- kurze Bestätigungs-, Hinweis- oder Fehlersignale.

Die Aufgabe wird immer in derselben Reihenfolge bearbeitet:

1. Effekt-Typ auswählen.
2. Genau ein Scaffold-Skript ausführen.
3. Den typbezogenen Fragenpfad durcharbeiten.
4. Farbmodell und Parameter festlegen.
5. Definition und Renderlogik vervollständigen.
6. Platzhalter entfernen.
7. Validieren, bauen und testen.

Die drei Skripte enthalten ihre Vorlagen vollständig in sich selbst. Sie
kopieren keine Template-Ordner und benötigen keine Flags oder Argumente. Beim
Start fragt jedes Skript ausschließlich nach dem Zielordner und erzeugt dort:

```text
<effect_id>/
├── effect.yaml
├── effect.py
└── presets.yaml
```

Die erzeugten Dateien sind **absichtlich noch nicht ausführbar**. Sichtbare
Platzhalter und `NotImplementedError` verhindern, dass ein unbearbeitetes
Scaffold versehentlich als fertiger Effekt verwendet wird.

Passt eine Anforderung nicht eindeutig in die Entscheidungen dieses Skills,
prüfe die aktuelle Projektdokumentation unter `docs/effect-system/`. Erfinde
keine zusätzlichen Verträge und ändere nicht eigenmächtig die Engine.

---

# 1. Effekt-Typ auswählen

## Theorie

Der Typ wird nach der fachlichen Rolle des Effekts ausgewählt. Das sichtbare
Muster allein reicht nicht. Ein Sweep kann beispielsweise State, Overlay oder
Event sein; entscheidend ist, wie er verwendet wird.

Im ersten Schritt muss **genau eine** der folgenden drei Optionen gewählt
werden.

## Option 1: State

Ein State ist eine gesetzte Zustandsanzeige. Er bildet den visuellen
Grundzustand und bleibt aktiv, bis er ersetzt oder entfernt wird.

Typische Beispiele:

- Bereitschaftszustand,
- Listening-State,
- dauerhaft pulsierender Ring,
- rotierender Processing-State,
- dauerhaftes Glimmen oder ein Scanner.

Grundstruktur erzeugen:

```powershell
python .\scripts\create_state.py
```

Danach mit **Abschnitt 2A – Fragenpfad für States** fortfahren.

## Option 2: Overlay

Ein Overlay ist eine zusätzliche Anzeige, die über einem bereits laufenden
State dargestellt wird. Es ersetzt nicht die fachliche Rolle des States,
sondern ergänzt oder überlagert ihn.

Typische Beispiele:

- temporärer Sweep,
- Fortschritts- oder Füllanzeige,
- Markierung oder hervorgehobenes Segment,
- zeitweise zusätzliche Ringanimation.

Grundstruktur erzeugen:

```powershell
python .\scripts\create_overlay.py
```

Danach mit **Abschnitt 2B – Fragenpfad für Overlays** fortfahren.

## Option 3: Event

Ein Event ist ein kurzes, einmalig ausgelöstes und priorisiertes Signal. Es
besitzt einen abgeschlossenen Ablauf und wird über die Event-Warteschlange
verarbeitet.

Typische Beispiele:

- Bestätigungspuls,
- Fehlerblitz,
- Warnsignal,
- kurzer Farbimpuls,
- kurzer umlaufender Sweep.

Grundstruktur erzeugen:

```powershell
python .\scripts\create_event.py
```

Danach mit **Abschnitt 2C – Fragenpfad für Events** fortfahren.

## Ergebnis dieses Abschnitts

Vor dem Fortfahren schriftlich festhalten:

```text
EFFECT_TYPE = STATE | OVERLAY | EVENT
SCAFFOLD_SCRIPT = scripts/create_state.py | scripts/create_overlay.py | scripts/create_event.py
TARGET_DIRECTORY = <erzeugter Effektordner>
```

Nicht mehrere Skripte für denselben Effekt ausführen.

---

# 2A. Fragenpfad für States

Diesen Abschnitt nur bearbeiten, wenn in Abschnitt 1 **State** gewählt wurde.

## Frage 1: Auf welchem State-Platz darf der Effekt eingesetzt werden?

### Option A: Nur Primary State

Wählen, wenn der Effekt ein normaler laufender Anwendungszustand ist.

Beispiele:

- Listening,
- Thinking,
- Recording,
- Speaking.

Folgen:

- nur `LayerId.STATE_LAYER`,
- keine persistente Speicherung als Background State,
- `restorable=False`.

### Option B: Nur Background State

Wählen, wenn der Effekt als unterster, wiederherstellbarer Grundzustand dienen
soll.

Folgen:

- nur `LayerId.BACKGROUND_STATE_LAYER`,
- `persistent_storage=True`,
- `restorable=True`.

### Option C: Background und Primary State

Wählen, wenn dieselbe Definition sinnvoll an beiden State-Plätzen eingesetzt
werden kann.

Folgen:

- beide Layerregeln deklarieren,
- Background-Regel mit `persistent_storage=True`,
- `restorable=True`.

Die einzutragenden Blöcke stehen in Abschnitt 6.1.

## Frage 2: Besitzt der Effekt eine frei laufende, regelbare Animation?

### Option A: Nein

Wählen, wenn die Darstellung während einer Invocation statisch bleibt.

Folge:

```python
animated=False
```

Kein Parameter `speed`.

### Option B: Ja

Wählen, wenn sich die Darstellung fortlaufend verändert und ihre
Grundgeschwindigkeit konfigurierbar sein soll.

Beispiele:

- Pulsieren,
- Blinken,
- Rotieren,
- Scanner,
- laufender Farbwechsel.

Folgen:

```python
animated=True
```

und verpflichtend ein Parameter namens `speed`. Die genaue Definition steht
in Abschnitt 5.2.

## Frage 3: Soll eine räumliche Bewegungsrichtung umkehrbar sein?

### Option A: Nein

Wählen bei:

- statischen Effekten,
- Pulsieren,
- Blinken,
- symmetrischen Effekten,
- Bewegungen mit bewusst festgelegter Richtung.

Folge:

```python
directional=False
```

Kein Parameter `reverse`.

### Option B: Ja

Wählen, wenn der Benutzer die Bewegungsrichtung umkehren können soll.

Beispiele:

- rotierender Punkt,
- rotierendes Segment,
- umlaufender Schweif,
- gerichteter Scanner.

Folgen:

```python
directional=True
```

und verpflichtend ein boolescher Parameter `reverse`. Die genaue Definition
steht in Abschnitt 5.3.

## Ergebnis des State-Pfads

```text
STATE_PLACEMENT = PRIMARY | BACKGROUND | BOTH
ANIMATED = true | false
DIRECTIONAL = true | false
```

Danach mit Abschnitt 3 fortfahren.

---

# 2B. Fragenpfad für Overlays

Diesen Abschnitt nur bearbeiten, wenn in Abschnitt 1 **Overlay** gewählt
wurde.

## Frage 1: Wer steuert Ablauf, Änderungen und Beendigung?

Die tatsächliche Nutzungsdauer allein entscheidet nicht zwischen den beiden
Overlay-Modi. Ein Controlled Overlay kann nur wenige Sekunden aktiv sein; ein
Timed Overlay kann relativ lange laufen.

### Option A: Timed Overlay

Wählen, wenn der vollständige Ablauf beim Aktivieren feststeht und die Engine
das Overlay nach einer festgelegten Dauer automatisch entfernen soll.

Typische Beispiele:

- Sweep über 1.500 ms,
- kurz eingeblendeter Ring,
- lokal ablaufender Countdown mit bereits bekannter Dauer,
- fest definierte Hervorhebung.

Folgen:

```python
overlay_mode=OverlayMode.TIMED
```

Zusätzlich:

- `duration_ms` oder `total_ms` ist verpflichtend,
- `runtime_input_schema={}` muss leer sein,
- `LayerId.TEMP_OVERLAY_LAYER`,
- `requires_finite_duration=True`,
- Playback-Modus `SINGLE_RUN`.

Für normale Effekte in diesem Skill wird bevorzugt `duration_ms` verwendet.

### Option B: Controlled Overlay

Wählen, wenn eine laufende Steuerung das Overlay setzt, bei Bedarf während der
Nutzung aktualisiert und anschließend gezielt entfernt.

Typische Beispiele:

- Fortschrittsanzeige,
- Füllstandsanzeige,
- laufend veränderte Pegelanzeige,
- zusätzliche Markierung, die gesetzt und später entfernt wird.

Folgen:

```python
overlay_mode=OverlayMode.CONTROLLED
```

Zusätzlich:

- kein verpflichtender Dauerparameter,
- `LayerId.ONGOING_OVERLAY_LAYER`,
- `requires_indefinite_duration=True` im technischen Typvertrag,
- das tatsächliche Overlay kann trotzdem nur kurz aktiv sein,
- das Ende erfolgt durch das Entfernen der kontrollierten Instanz.

## Frage 2: Werden Werte während der aktiven Nutzung aktualisiert?

Diese Frage ist nur bei einem Controlled Overlay relevant.

### Option A: Nein

Die stabile Darstellung wird vollständig aus `parameter_schema` und
`defaults` berechnet.

Folge:

```python
runtime_input_schema={}
```

### Option B: Ja

Deklariere unter `runtime_input_schema` ausschließlich die Werte, die sich
während der aktiven Nutzung verändern dürfen.

Beispiel für einen Fortschrittswert:

```python
runtime_input_schema={
    "progress": EffectParamDefinition(
        name="progress",
        type="float",
        default=0.0,
        minimum=0.0,
        maximum=100.0,
        unit="percent",
    )
}
```

Diese Werte gehören nicht in `defaults` der stabilen Konfiguration und nicht
in `presets.yaml`. Der Renderer liest sie über `ctx.inputs`.

Bei einem Timed Overlay muss diese Entscheidung immer lauten:

```python
runtime_input_schema={}
```

## Frage 3: Soll das Overlay transparent oder deckend komponiert werden?

### Option A: Transparent

Wählen, wenn nur bestimmte LEDs beeinflusst werden und der darunterliegende
State an den übrigen Positionen sichtbar bleiben soll.

Folgen:

```python
composition=CompositionMode.TRANSPARENT
```

- `supports_transparency=True`,
- `allows_transparency=True`,
- unbeteiligte LED-Positionen als `None` zurückgeben.

Dies ist für die meisten Overlays die passende Option.

### Option B: Opaque

Wählen, wenn das Overlay für jede LED bewusst einen konkreten Wert liefert und
den darunterliegenden Inhalt vollständig ersetzen soll.

Folgen:

```python
composition=CompositionMode.OPAQUE
```

- `supports_transparency=False`,
- `allows_transparency=False`,
- jede Position erhält einen RGB-Integer.

## Ergebnis des Overlay-Pfads

```text
OVERLAY_MODE = TIMED | CONTROLLED
HAS_RUNTIME_INPUTS = true | false
COMPOSITION = TRANSPARENT | OPAQUE
```

Danach mit Abschnitt 3 fortfahren.

---

# 2C. Fragenpfad für Events

Diesen Abschnitt nur bearbeiten, wenn in Abschnitt 1 **Event** gewählt wurde.

## Frage 1: Welche Dauer passt zum sichtbaren Ablauf?

Ein Event ist immer endlich. Das Scaffold enthält deshalb bereits den
Pflichtparameter `duration_ms`.

Festlegen:

- sinnvoller Default,
- sinnvolles Minimum,
- optional ein Maximum.

Beispiele:

```text
sehr kurzer Blitz:       etwa 100 bis 250 ms
kurzer Impuls:           etwa 300 bis 700 ms
weicher Puls oder Sweep: etwa 600 bis 1500 ms
```

Die Werte sind keine festen Vorgaben. Sie müssen zur konkreten sichtbaren
Logik passen.

## Frage 2: Soll das Event transparent oder deckend komponiert werden?

### Option A: Transparent

Wählen, wenn das Event nur einzelne LEDs oder Segmente überlagern soll.

Folgen:

```python
composition=CompositionMode.TRANSPARENT
supports_transparency=True
```

Unbeteiligte LEDs bleiben `None`.

### Option B: Opaque

Wählen, wenn das Event den kompletten Ring bewusst ersetzt.

Folgen:

```python
composition=CompositionMode.OPAQUE
supports_transparency=False
```

Jede LED erhält einen konkreten Farbwert.

## Frage 3: Darf die Dauer beim Auslösen überschrieben werden?

### Option A: Nein

Die Dauer wird nur über den aufgelösten Parameter `duration_ms` bestimmt.

```python
supports_duration_override=False
```

### Option B: Ja

Ein Aufrufer darf für die Invocation eine abweichende Dauer festlegen.

```python
supports_duration_override=True
```

Die Renderlogik berücksichtigt dann zuerst
`ctx.invocation.requested_duration_ms` und verwendet ansonsten
`params["duration_ms"]`.

## Ergebnis des Event-Pfads

```text
DEFAULT_DURATION_MS = <Wert>
MIN_DURATION_MS = <Wert>
MAX_DURATION_MS = <Wert oder none>
COMPOSITION = TRANSPARENT | OPAQUE
SUPPORTS_DURATION_OVERRIDE = true | false
```

Danach mit Abschnitt 3 fortfahren.

---

# 3. Gemeinsame Basiseigenschaften festlegen

## Theorie

Nach dem typbezogenen Fragenpfad werden die gemeinsamen visuellen Merkmale
festgelegt. Dabei sind `animated` und `directional` keine bloßen
Beschreibungen, sondern lösen verbindliche Schemaanforderungen aus.

## Entscheidung 1: `animated`

### Option A: `animated=False`

Wählen, wenn kein konfigurierbarer `speed`-Multiplikator vorgesehen ist.

Wichtig: Ein endlicher Effekt darf sich trotzdem anhand seines
Dauerfortschritts verändern. Ein Countdown oder Event kann Frames aus
`elapsed / duration` berechnen und dennoch `animated=False` verwenden, wenn
kein eigener Geschwindigkeitsparameter angeboten wird.

### Option B: `animated=True`

Wählen, wenn der Effekt eine frei laufende Animation besitzt und `speed` als
konfigurierbarer Multiplikator angeboten wird.

Dann ist `speed` verpflichtend.

## Entscheidung 2: `directional`

### Option A: `directional=False`

Wählen, wenn keine umkehrbare Bewegungsrichtung angeboten wird.

### Option B: `directional=True`

Wählen, wenn der Benutzer die Richtung umschalten können soll.

Dann ist ein boolescher Parameter `reverse` verpflichtend.

## Entscheidung 3: `composition`

### Option A: `CompositionMode.OPAQUE`

Jede LED-Position enthält einen RGB-Integer. `0x000000` ist ein konkreter
schwarzer Wert und verdeckt einen darunterliegenden Layer.

### Option B: `CompositionMode.TRANSPARENT`

Unbeteiligte Positionen enthalten `None`; nur gesetzte Positionen verändern
das darunterliegende Bild.

Bei transparenter Komposition müssen Capability und LayerRule ebenfalls
Transparenz erlauben.

## Entscheidungsergebnis vollständig notieren

Vor Abschnitt 4 einen kompakten Entscheidungsblock erstellen:

```text
EFFECT_TYPE = ...
STATE_PLACEMENT = ...              # nur State
OVERLAY_MODE = ...                 # nur Overlay
HAS_RUNTIME_INPUTS = ...           # nur Controlled Overlay
DEFAULT_DURATION_MS = ...          # Timed Overlay oder Event
ANIMATED = true | false
DIRECTIONAL = true | false
COMPOSITION = OPAQUE | TRANSPARENT
SUPPORTS_DURATION_OVERRIDE = ...   # sofern relevant
```

Die Implementierung darf diesen Entscheidungen später nicht widersprechen.

---

# 4. Das richtige Farbmodell wählen

## Theorie

`color_model` beschreibt die konfigurierbaren Hauptfarben der Definition. Es
bestimmt verbindlich, welche Felder in `parameter_schema` vorhanden sein
müssen.

Wähle genau **eine** Option. Verwende nicht automatisch `MONO`, sondern wähle
nach der tatsächlich gewünschten Konfiguration.

## Option 1: `ColorModel.NONE`

Wählen, wenn der Effekt keine konfigurierbare Farbe besitzt.

Pflichtfelder:

```text
keine Farbfelder
kein brightness
```

Die Felder `color`, `secondary_color`, `colors`, `gradient`, `color_range` und
`random_seed` dürfen dann nicht deklariert werden.

## Option 2: `ColorModel.MONO`

Wählen, wenn eine konfigurierbare Hauptfarbe genügt.

Pflichtfelder:

```text
color
brightness
```

Beispiele:

- einfarbiger Puls,
- einfarbiges Segment,
- einfarbiger Scanner.

## Option 3: `ColorModel.DUAL`

Wählen, wenn zwei gleichwertige konfigurierbare Farben benötigt werden.

Pflichtfelder:

```text
color
secondary_color
brightness
```

`background_color` ist ein zusätzlicher normaler Parameter und ersetzt nicht
`secondary_color` im DUAL-Vertrag.

## Option 4: `ColorModel.PALETTE`

Wählen, wenn eine geordnete Liste aus mehreren Farben konfiguriert wird.

Pflichtfelder:

```text
colors
brightness
```

`colors` verwendet den Typ `color_list`.

## Option 5: `ColorModel.GRADIENT`

Wählen, wenn der Benutzer einen geordneten Farbverlauf mit Farbstopps
konfigurieren soll.

Pflichtfelder:

```text
gradient
brightness
```

`gradient` verwendet den Typ `gradient`.

## Option 6: `ColorModel.RANDOM_RANGE`

Wählen, wenn reproduzierbare Zufallsfarben aus einem begrenzten Farbbereich
erzeugt werden.

Pflichtfelder:

```text
color_range
random_seed
brightness
```

`color_range` verwendet den Typ `color_range`, `random_seed` den Typ `int`.

## Verbindliche Helligkeitsdefinition für farbige Modelle

Bei jedem Modell außer `NONE` muss exakt ein `brightness`-Parameter mit diesem
Vertrag vorhanden sein:

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

## Ergebnis dieses Abschnitts

```text
COLOR_MODEL = NONE | MONO | DUAL | PALETTE | GRADIENT | RANDOM_RANGE
REQUIRED_COLOR_PARAMETERS = <Liste>
```

Alle Pflichtfelder müssen anschließend synchron in `parameter_schema`,
`defaults` und den passenden Presets vorkommen.

---

# 5. Parameter festlegen

## 5.1 Theorie und Grundregel

`parameter_schema` enthält ausschließlich stabile, konfigurierbare Werte der
Definition. Jeder Parameter benötigt einen eindeutigen Namen, Typ, Default und
sinnvolle Grenzen.

Füge nur Parameter hinzu, die die konkrete Darstellung tatsächlich benötigt.
Zu viele Regler machen Effekte schwer verständlich und schwer testbar.

Allgemeines Muster:

```python
"parameter_name": EffectParamDefinition(
    name="parameter_name",
    type="float",
    default=1.0,
    minimum=0.0,
    maximum=5.0,
    description="Klare fachliche Bedeutung.",
    unit="multiplier",
)
```

Der Dictionary-Schlüssel und `name` müssen identisch sein.

## 5.2 Option: regelbare Animation

Nur verwenden, wenn in Abschnitt 3 `animated=True` gewählt wurde.

```python
"speed": EffectParamDefinition(
    name="speed",
    type="float",
    default=1.0,
    minimum=0.1,
    maximum=5.0,
    description="Multiplikator der entworfenen Grundgeschwindigkeit.",
    unit="multiplier",
)
```

Es gibt keine separaten Parameter `speed_min` und `speed_max`. Minimum und
Maximum gehören zur Definition von `speed`.

`speed` ist keine FPS-Angabe. `speed=1.0` bezeichnet die entworfene
Grundgeschwindigkeit.

## 5.3 Option: umkehrbare Richtung

Nur verwenden, wenn in Abschnitt 3 `directional=True` gewählt wurde.

```python
"reverse": EffectParamDefinition(
    name="reverse",
    type="bool",
    default=False,
    description="Kehrt die Bewegungsrichtung um.",
)
```

Die Renderlogik muss den Wert tatsächlich verwenden.

## 5.4 Pflichtoption: endlicher Ablauf

Timed Overlays und Events benötigen `duration_ms` oder `total_ms`. In diesem
Skill wird bevorzugt `duration_ms` verwendet:

```python
"duration_ms": EffectParamDefinition(
    name="duration_ms",
    type="duration_ms",
    default=1000,
    minimum=1,
    description="Gesamtdauer des Ablaufs.",
    unit="ms",
)
```

Der Default ist an den sichtbaren Ablauf anzupassen.

## 5.5 Häufige optionale Parameter

Diese Namen sind keine Pflicht und nur bei echtem Bedarf zu verwenden:

| Parameter | Sinnvolle Bedeutung |
|---|---|
| `background_color` | konkrete Hintergrundfarbe der Darstellung |
| `segment_length` | Anzahl der LEDs eines Segments |
| `trail_length` | Länge eines Schweifs |
| `falloff` | Abfall der Helligkeit nach außen |
| `min_brightness` | untere Helligkeitsgrenze eines Pulses |
| `max_brightness` | obere Helligkeitsgrenze eines Pulses |
| `width` | allgemeine Breite einer Markierung oder Fläche |
| `start_led` | konfigurierter Startindex |
| `duty_cycle` | sichtbarer Anteil einer Blinkperiode |

Für Werte, die von `ctx.led_count` abhängen, keine starre maximale LED-Anzahl
als Renderannahme verwenden. Der Renderer begrenzt die effektive Länge auf
`ctx.led_count`.

## 5.6 Unterstützte Parametertypen

```text
bool
int
float
duration_ms
angle_deg
enum
color
color_list
gradient
color_range
```

Der Renderer erhält bereits kanonische und validierte Werte. Er implementiert
keine zweite Eingabesprache für Farbnamen, Dauertexte oder Bool-Aliase.

## 5.7 Runtime-Werte eines Controlled Overlays

Nur ein Controlled Overlay darf `runtime_input_schema` verwenden. Dort stehen
nur Werte, die während der aktiven Nutzung verändert werden.

Beispiele:

```text
progress
level
remaining
position
```

Diese Felder:

- gehören nicht in `EffectDefinition.defaults`,
- gehören nicht in `presets.yaml`,
- werden in `render()` über `ctx.inputs` gelesen.

Timed Overlays, States und Events verwenden immer:

```python
runtime_input_schema={}
```

beziehungsweise lassen das Feld vollständig weg, sofern das Scaffold es nicht
enthält.

## Ergebnis dieses Abschnitts

Eine vollständige Liste erstellen:

```text
CONFIG_PARAMETERS:
- <name>: <type>, default=<wert>, min=<wert>, max=<wert>

RUNTIME_INPUTS:             # nur Controlled Overlay
- <name>: <type>, default=<wert>, min=<wert>, max=<wert>
```

Danach `parameter_schema`, `runtime_input_schema` und `defaults` eintragen.

---

# 6. Capabilities und LayerRules eintragen

Die folgenden Blöcke sind die typgerechten Ausgangspunkte. Ersetze die
Platzhalter im erzeugten Scaffold durch genau den Block, der zu den bisherigen
Entscheidungen passt.

Verwende für `<ALLOW_TRANSPARENCY>`:

```text
True  bei CompositionMode.TRANSPARENT
False bei CompositionMode.OPAQUE
```

## 6.1 State

### Option A: Nur Primary State

```python
capabilities=EffectCapabilities(
    playback_modes=(PlaybackMode.LOOP,),
    supports_transparency=<ALLOW_TRANSPARENCY>,
    restorable=False,
),
layer_rules={
    LayerId.STATE_LAYER: LayerRule(
        allowed=True,
        allowed_playback_modes=(PlaybackMode.LOOP,),
        requires_indefinite_duration=True,
        allows_transparency=<ALLOW_TRANSPARENCY>,
    )
},
```

### Option B: Nur Background State

```python
capabilities=EffectCapabilities(
    playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
    supports_transparency=<ALLOW_TRANSPARENCY>,
    restorable=True,
),
layer_rules={
    LayerId.BACKGROUND_STATE_LAYER: LayerRule(
        allowed=True,
        allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
        requires_indefinite_duration=True,
        allows_transparency=<ALLOW_TRANSPARENCY>,
        persistent_storage=True,
    )
},
```

### Option C: Background und Primary State

```python
capabilities=EffectCapabilities(
    playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
    supports_transparency=<ALLOW_TRANSPARENCY>,
    restorable=True,
),
layer_rules={
    LayerId.BACKGROUND_STATE_LAYER: LayerRule(
        allowed=True,
        allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
        requires_indefinite_duration=True,
        allows_transparency=<ALLOW_TRANSPARENCY>,
        persistent_storage=True,
    ),
    LayerId.STATE_LAYER: LayerRule(
        allowed=True,
        allowed_playback_modes=(PlaybackMode.LOOP,),
        requires_indefinite_duration=True,
        allows_transparency=<ALLOW_TRANSPARENCY>,
    ),
},
```

## 6.2 Overlay

### Option A: Timed Overlay

Voraussetzungen:

```python
overlay_mode=OverlayMode.TIMED
runtime_input_schema={}
```

Capabilities und LayerRule:

```python
capabilities=EffectCapabilities(
    playback_modes=(PlaybackMode.SINGLE_RUN,),
    supports_transparency=<ALLOW_TRANSPARENCY>,
    supports_duration_override=<TRUE_OR_FALSE>,
),
layer_rules={
    LayerId.TEMP_OVERLAY_LAYER: LayerRule(
        allowed=True,
        allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
        requires_finite_duration=True,
        allows_transparency=<ALLOW_TRANSPARENCY>,
    )
},
```

`parameter_schema` muss `duration_ms` oder `total_ms` enthalten.

### Option B: Controlled Overlay

Voraussetzung:

```python
overlay_mode=OverlayMode.CONTROLLED
```

Capabilities und LayerRule für normale kontrollierte Anzeigen:

```python
capabilities=EffectCapabilities(
    playback_modes=(PlaybackMode.LOOP,),
    supports_transparency=<ALLOW_TRANSPARENCY>,
    restorable=False,
    data_driven=<TRUE_IF_RUNTIME_INPUTS_ELSE_FALSE>,
),
layer_rules={
    LayerId.ONGOING_OVERLAY_LAYER: LayerRule(
        allowed=True,
        allowed_playback_modes=(PlaybackMode.LOOP,),
        requires_indefinite_duration=True,
        allows_transparency=<ALLOW_TRANSPARENCY>,
    )
},
```

Kein verpflichtender Dauerparameter. Das technische
`requires_indefinite_duration=True` bedeutet, dass die Engine kein
automatisches Ende aus einer Effektdauer berechnet. Es sagt nicht, wie lange
die Anzeige in der realen Nutzung aktiv bleibt.

## 6.3 Event

Das Event-Scaffold enthält die feste Grundstruktur bereits. Ersetze nur:

```text
<SUPPORTS_TRANSPARENCY>
<SUPPORTS_DURATION_OVERRIDE>
```

entsprechend den Entscheidungen aus Abschnitt 2C.

Der Event-Vertrag bleibt:

```python
playback_modes=(PlaybackMode.SINGLE_RUN,)
supports_queueing=True
requires_finite_duration=True
queue_mode=QueueMode.PRIORITY_FIFO
```

## Kontrollpunkt

Prüfen:

- Layer gehört zum gewählten Typ.
- Timed Overlay und Event verlangen endliche Dauer.
- State und Controlled Overlay verlangen technisch unbestimmte Dauer.
- Transparenzwerte stimmen in `composition`, Capability und LayerRule überein.
- Event besitzt Queueing; State und Overlay nicht.

---

# 7. Renderlogik implementieren

## 7.1 Framevertrag

Jeder Aufruf muss eine vollständige Liste liefern:

```python
len(frame) == ctx.led_count
```

Nie eine feste Anzahl von zwölf LEDs codieren.

### Opaque

```python
frame: list[int | None] = [0x000000] * ctx.led_count
```

Jede Position enthält einen RGB-Integer.

### Transparent

```python
frame: list[int | None] = [None] * ctx.led_count
```

Nur beteiligte Positionen werden gesetzt. `None` erhält den darunterliegenden
Wert; `0x000000` ist dagegen sichtbares Schwarz.

## 7.2 Parameter und Farben lesen

Stabile Werte:

```python
params = {**ctx.definition.defaults, **ctx.params}
```

Runtime-Werte eines Controlled Overlays:

```python
inputs = dict(ctx.inputs)
```

Kanonischen Hexwert in einen RGB-Integer umwandeln:

```python
def _color(value: str) -> int:
    return int(value.removeprefix("#"), 16)
```

Für Helligkeit bevorzugt die vorhandene Funktion:

```python
from src.core.color_math import scale_color

color = scale_color(_color(params["color"]), float(params["brightness"]))
```

Keine eigenen Farbnamen oder Eingabealiase parsen.

## 7.3 Zeit korrekt berechnen

### Frei laufende Animation

```python
elapsed = max(0.0, ctx.now - ctx.invocation.created_at)
speed = float(params["speed"])
```

Alle Phasen und Positionen werden aus `elapsed` berechnet. Keine
Framezähler, Timer oder veränderlichen Klassenvariablen als Zeitquelle.

### Endlicher Ablauf

```python
duration_ms = int(params["duration_ms"])
elapsed_ms = max(0.0, (ctx.now - ctx.invocation.created_at) * 1000.0)
progress = max(0.0, min(1.0, elapsed_ms / max(1.0, float(duration_ms))))
```

Bei erlaubtem Duration-Override:

```python
duration_ms = int(
    ctx.invocation.requested_duration_ms
    if ctx.invocation.requested_duration_ms is not None
    else params["duration_ms"]
)
```

`progress` liegt anschließend zwischen `0.0` und `1.0`.

### Umkehrbare Richtung

```python
step_sign = -1 if bool(params["reverse"]) else 1
```

## 7.4 Visuelle Grundmuster

Die folgenden Muster sind Ausgangspunkte. Passe Konstanten und Parameter an
den gewünschten Effekt an.

### Statischer Vollring

```python
color = scale_color(_color(params["color"]), float(params["brightness"]))
return [color] * ctx.led_count
```

### Weicher Puls

```python
import math

phase = (elapsed * speed) % 1.0
intensity = 0.5 - 0.5 * math.cos(2.0 * math.pi * phase)
color = scale_color(_color(params["color"]), intensity * float(params["brightness"]))
return [color] * ctx.led_count
```

### Blinken

```python
phase = (elapsed * speed) % 1.0
visible = phase < float(params.get("duty_cycle", 0.5))
color = scale_color(_color(params["color"]), float(params["brightness"]))
return [color if visible else 0x000000] * ctx.led_count
```

Bei transparentem Blinken statt Schwarz `None` verwenden.

### Rotierender Punkt

```python
position = int(elapsed * speed * ctx.led_count) % ctx.led_count
if bool(params.get("reverse", False)):
    position = (-position) % ctx.led_count

frame: list[int | None] = [0x000000] * ctx.led_count
frame[position] = scale_color(_color(params["color"]), float(params["brightness"]))
return frame
```

Für transparente Komposition mit `[None] * ctx.led_count` beginnen.

### Rotierendes Segment mit Ringumbruch

```python
length = max(1, min(int(params["segment_length"]), ctx.led_count))
start = int(elapsed * speed * ctx.led_count)
step_sign = -1 if bool(params.get("reverse", False)) else 1

frame: list[int | None] = [0x000000] * ctx.led_count
color = scale_color(_color(params["color"]), float(params["brightness"]))
for offset in range(length):
    index = (start + offset * step_sign) % ctx.led_count
    frame[index] = color
return frame
```

### Segment mit weichem Schweif

```python
trail_length = max(1, min(int(params["trail_length"]), ctx.led_count))
head = int(elapsed * speed * ctx.led_count)
step_sign = -1 if bool(params.get("reverse", False)) else 1

frame: list[int | None] = [None] * ctx.led_count
base = _color(params["color"])
brightness = float(params["brightness"])

for distance in range(trail_length):
    ratio = 1.0 - distance / max(1, trail_length)
    index = (head - distance * step_sign) % ctx.led_count
    frame[index] = scale_color(base, brightness * ratio)
return frame
```

### Endlicher Sweep

```python
position = min(
    ctx.led_count - 1,
    int(progress * ctx.led_count),
)
frame: list[int | None] = [None] * ctx.led_count
frame[position] = scale_color(_color(params["color"]), float(params["brightness"]))
return frame
```

### Fortschrittsfüllung

```python
progress = max(0.0, min(100.0, float(inputs["progress"]))) / 100.0
filled = int(round(progress * ctx.led_count))
frame: list[int | None] = [None] * ctx.led_count
color = scale_color(_color(params["color"]), float(params["brightness"]))
for index in range(filled):
    frame[index] = color
return frame
```

## 7.5 Qualitätsregeln für Renderlogik

- Gleicher Zeitpunkt plus gleiche Werte ergibt denselben Frame.
- Andere Render-FPS verändert nicht die reale Geschwindigkeit.
- Ringindizes immer mit `% ctx.led_count` umbrechen.
- Längen auf `0..ctx.led_count` begrenzen.
- Division durch null verhindern.
- Zwischenwerte auf ihre gültigen Bereiche begrenzen.
- Keine Effektdaten außerhalb der Invocation als versteckten Zustand halten.
- Keine Threads, Timer, Nebenprozesse oder blockierende Arbeit starten.

---

# 8. IDs, Metadaten und Dateien vervollständigen

## 8.1 Zielpfad

First-Party-Quellen liegen typabhängig unter:

```text
tools/effect_building/sources/states/<effect_id>/
tools/effect_building/sources/overlays/<effect_id>/
tools/effect_building/sources/events/<effect_id>/
```

## 8.2 Namen

Festlegen:

```text
effect_id     = aussagekräftiges snake_case
class_name    = aussagekräftiges PascalCase
source_id     = vorhandener Quellenraum des Projekts
package_id    = normalerweise <source_id>.<effect_id>
title         = kurzer lesbarer Titel
description   = ein klarer Satz über die sichtbare Wirkung
```

Vor dem Schreiben nach vorhandenen Definition- und Preset-IDs suchen.

## 8.3 `effect.yaml`

Alle Platzhalter ersetzen:

```yaml
package_id: <source_id>.<effect_id>
source_id: <source_id>
entry_class: <ClassName>
min_service_version: 1.0.0
```

`entry_class` muss exakt dem Klassennamen in `effect.py` entsprechen.

## 8.4 `effect.py`

Verbindlich:

- genau eine lokal definierte `BaseEffect`-Unterklasse,
- vollständige `EffectDefinition`,
- exakt eine konkrete `render()`-Implementierung,
- keine zweite ungenutzte Effektklasse,
- keine Platzhalter,
- kein `NotImplementedError`.

## 8.5 Tags

Wenige fachliche Tags verwenden, beispielsweise:

```python
tags=("state", "pulse", "animated")
```

Keine langen Synonymlisten anlegen.

---

# 9. Defaults und Presets

## 9.1 Defaults

Für jeden Konfigurationsparameter einen auflösbaren Standardwert anlegen.

Diese Stellen müssen synchron sein:

```text
parameter_schema[<name>].default
defaults[<name>]
Preset-Wert, falls im Preset gesetzt
```

`defaults` darf keine unbekannten Felder enthalten.

## 9.2 Presets

Presets sind kuratierte Ausgangskonfigurationen derselben Definition.

Sie dürfen nur Felder aus `parameter_schema` enthalten. Sie verändern niemals:

- Definitionstyp,
- Overlay-Modus,
- Layer,
- Capabilities,
- Lebenszyklus,
- Runtime-Eingaben.

Für normale Effekte reichen meist ein bis drei aussagekräftige Presets.

Beispiel:

```yaml
presets:
  calm_blue_pulse:
    title: "Calm Blue Pulse"
    description: "Langsamer, zurückhaltender blauer Puls."
    params:
      color: "#3388FF"
      brightness: 0.65
      speed: 0.7
    tags:
      - calm
      - pulse
```

Bei Controlled Overlays gehören Werte aus `runtime_input_schema` nicht in
Presets.

---

# 10. Scaffold vollständig bereinigen

Die Scaffold-Dateien sind absichtlich ungültig. Vor der Validierung muss jeder
Pflichtplatzhalter entfernt werden.

Im Effektordner ausführen:

```powershell
rg -n "<[A-Z0-9_]+>|raise\s+NotImplementedError|TODO" .
```

Das Ergebnis muss leer sein.

Anschließend Python-Syntax prüfen:

```powershell
python -m py_compile .\effect.py
```

Zusätzlich manuell prüfen:

- Klassenname in `effect.py` und `entry_class` stimmen überein.
- Definition-ID und Ordnername sind konsistent.
- `parameter_schema`, `defaults` und Presets sind synchron.
- Timed Overlay und Event besitzen eine Dauer.
- Nur Controlled Overlay besitzt Runtime-Eingaben.
- `animated=True` besitzt `speed`.
- `directional=True` besitzt boolesches `reverse`.
- Farbmodell und Farbparameter passen zusammen.
- Composition und Transparenzflags passen zusammen.

---

# 11. Validieren, bauen und testen

## 11.1 Quellenvalidierung

```powershell
python .\tools\effect_packager.py validate-effect-source <EFFEKTPFAD>
```

Jeden Fehler an der Quelle korrigieren. Die Validierung nicht umgehen.

## 11.2 Paket bauen

```powershell
python .\tools\effect_packager.py pack-effect `
  <EFFEKTPFAD> `
  <AUSGABE>.lefx
```

## 11.3 Paket verifizieren

```powershell
python .\tools\effect_packager.py verify-effect-package <AUSGABE>.lefx
```

## 11.4 First-Party-Gesamtbuild

Nur wenn der Effekt in das First-Party-Set aufgenommen werden soll:

```powershell
python .\tools\effect_building\build_lefxset.py --rebuild-packages
```

## 11.5 Verhalten prüfen

Mindestens diese Fälle prüfen:

- Frame direkt am Start,
- Frame zu einem späteren Zeitpunkt,
- bei endlichen Effekten: Anfang, Mitte und Ende,
- minimale und maximale Parameterwerte,
- `speed` kleiner, gleich und größer als `1.0`, falls vorhanden,
- `reverse=False` und `reverse=True`, falls vorhanden,
- Ringumbruch an Index `0`,
- exakt `ctx.led_count` Werte,
- zusätzlich eine LED-Anzahl ungleich zwölf,
- Transparenz oder Deckung wie deklariert,
- Controlled Overlay mit minimalem und maximalem Runtime-Wert,
- Presets lassen sich vollständig auflösen.

Der Packager-Smoke-Render ersetzt diese gezielten Tests nicht.

---

# 12. Abschlussbericht

Nach erfolgreicher Arbeit knapp berichten:

1. erstellte oder geänderte Dateien,
2. gewählter Typ und typbezogene Entscheidungen,
3. Farbmodell,
4. Konfigurationsparameter und gegebenenfalls Runtime-Eingaben,
5. sichtbare Renderlogik,
6. vorhandene Presets,
7. ausgeführte Prüf-, Build- und Testbefehle,
8. tatsächliche Ergebnisse.

Keinen erfolgreichen Test behaupten, der nicht ausgeführt wurde.

---

# 13. Harte Regeln

- Immer genau eines der drei Scaffold-Skripte verwenden.
- Keine Template-Ordner anlegen oder kopieren.
- Keine Scaffold-Platzhalter im fertigen Effekt belassen.
- Keine Engineänderung vornehmen, um einen einzelnen Effekt möglich zu machen.
- Keine Controller-, Service- oder Registry-Module importieren.
- Keine anderen LEFX-Pakete importieren.
- Keine gemeinsame `common.py` für mehrere Effekte erstellen.
- Nur erlaubte Standardbibliotheken, `src.core.effect_schema`,
  `src.core.color_math` und paketlokale relative Importe verwenden.
- Keine Threads, Timer, Nebenprozesse oder Framezähler als Zeitquelle.
- Keine feste LED-Anzahl codieren.
- Keine unbekannten Parameter still ignorieren.
- Keine Eingabeparser für bereits kanonische Werte in `render()` bauen.
- Keine unnötigen Parameter hinzufügen.
- Keine Teilimplementierung als fertigen Effekt ausgeben.

## Maßgebliche Dokumentation

Bei Widersprüchen ist die aktuelle Projektdokumentation maßgeblich:

- `docs/effect-system/03_layers_and_composition.md`
- `docs/effect-system/04_effect_types_and_lifecycles.md`
- `docs/effect-system/05_schema_v2.md`
- `docs/effect-system/06_parameters_and_values.md`
- `docs/effect-system/08_packages_ids_and_configuration.md`
- `docs/effect-system/10_validation_and_build.md`
