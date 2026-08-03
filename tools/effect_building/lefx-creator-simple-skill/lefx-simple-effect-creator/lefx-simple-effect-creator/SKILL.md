---
name: lefx-simple-effect-creator
description: Erstellt robuste, eigenständige LEFX-V2-Effektquellen für normale States, zeitgesteuerte Overlays und Events wie Pulsieren, Rotieren, Blinken, Segmente, Sweeps und kurze Lichtsignale.
---

# LEFX Simple Effect Creator

## Ziel

Erstelle vollständige, validierbare LEFX-V2-Quellen für normale visuelle Effekte.
Die Darstellung wird ausschließlich aus diesen Werten berechnet:

- stabiler Effektkonfiguration,
- `ctx.now` und `ctx.invocation.created_at`,
- `ctx.led_count`,
- dem unveränderlichen V2-Vertrag der Definition.

Dieser Skill ist absichtlich auf einfache, eigenständige Effekte begrenzt.
Passt eine Anforderung nicht eindeutig in diesen Umfang, lies zuerst
`docs/effect-system/README.md` und die dort verlinkte aktuelle Referenz. Rate
nicht und erweitere den Vertrag nicht aus eigener Initiative.

## Unterstützte Formen

Verwende diesen Skill nur für:

1. **State** – unbestimmter visueller Grundzustand.
2. **Timed Overlay** – endliche Einblendung, deren Ablauf beim Aktivieren feststeht.
3. **Event** – kurzes, priorisiertes und endliches Signal.

Typische Effekte:

- statische Farbe,
- weiches Pulsieren oder Atmen,
- Blinken,
- rotierender Punkt oder rotierendes Segment,
- Scanner und Radar-Sweep,
- rotierender Farbverlauf,
- kurzer Puls, Blitz oder Sweep,
- lokal ablaufender Countdown oder Timer.

## Verbindlicher Arbeitsablauf

Führe die Schritte immer in dieser Reihenfolge aus. Überspringe keinen Schritt.

### 1. Wunsch in einen klaren Effektvertrag übersetzen

Bestimme:

- sichtbares Verhalten,
- Lebensdauer,
- gewünschte Farben,
- sinnvolle Konfigurationsparameter,
- transparente oder deckende Darstellung,
- Bewegung und Bewegungsrichtung,
- endliche Dauer, falls erforderlich.

Stelle höchstens eine Rückfrage, wenn der Lebenszyklus oder die gewünschte
Darstellung nicht sinnvoll ableitbar ist. Erfinde keine zusätzlichen
Funktionen, die nicht benötigt werden.

### 2. Typ festlegen

Nutze diese Entscheidung:

```text
Unbestimmter Grundzustand?               -> State
Endliche Einblendung über dem State?     -> Timed Overlay
Kurzes priorisiertes Einmalsignal?       -> Event
```

Die sichtbare Form allein bestimmt den Typ nicht. Ein Sweep kann State,
Timed Overlay oder Event sein; entscheidend ist sein Lebenszyklus.

Lies bei Unsicherheit `references/TYPE_AND_FILE_RULES.md`.

### 3. Zielpfad und IDs festlegen

First-Party-Quellen liegen unter:

```text
tools/effect_building/sources/states/<effect_id>/
tools/effect_building/sources/overlays/<effect_id>/
tools/effect_building/sources/events/<effect_id>/
```

Regeln:

- `effect_id`: aussagekräftiges `snake_case`.
- Klassenname: aussagekräftiges `PascalCase`, vorzugsweise mit Typbezug.
- `package_id`: normalerweise `<source_id>.<effect_id>`.
- Definition-ID und Preset-IDs müssen global eindeutig sein.
- Suche vor dem Schreiben nach vorhandenen IDs und ähnlichen Effekten.

### 4. Gültiges Grundgerüst erzeugen

Bevorzugt:

```powershell
python .\tools\effect_packager.py init-effect <zielordner> `
  --effect-id <effect_id> `
  --source-id <source_id> `
  --title "<Titel>" `
  --type state
```

Für ein Timed Overlay:

```powershell
python .\tools\effect_packager.py init-effect <zielordner> `
  --effect-id <effect_id> `
  --source-id <source_id> `
  --title "<Titel>" `
  --type overlay `
  --overlay-mode timed
```

Für ein Event:

```powershell
python .\tools\effect_packager.py init-effect <zielordner> `
  --effect-id <effect_id> `
  --source-id <source_id> `
  --title "<Titel>" `
  --type event
```

Falls kein Scaffold ausgeführt werden kann, kopiere das nächstliegende Beispiel
unter `examples/` und ersetze IDs, Klasse, Metadaten, Parameter und Renderlogik
vollständig.

### 5. Die drei Quelldateien vollständig erstellen

Jede fertige Quelle enthält:

```text
<effect_id>/
├── effect.yaml
├── effect.py
└── presets.yaml
```

- `effect.yaml`: Paket-, Quellen- und Einstiegsklasse.
- `effect.py`: genau eine lokal definierte `BaseEffect`-Unterklasse mit
  `EffectDefinition` und `render()`.
- `presets.yaml`: wenige sinnvolle Konfigurationsvorschläge derselben Definition.

Keine fertige Datei darf `TODO`, Platzhalter oder nicht implementierte Zweige
enthalten.

### 6. Parameter klein und verständlich halten

Deklariere nur Parameter, die die gewünschte Darstellung wirklich benötigt.
Nutze die Standardnamen konsequent:

| Merkmal | Pflicht-/Standardfeld |
|---|---|
| farbiger Effekt | `brightness` als `float` von `0.0` bis `1.0` |
| animierter Effekt mit Geschwindigkeitssteuerung | `speed` |
| umkehrbare Bewegungsrichtung | `reverse` als `bool` |
| endlicher Effekt | `duration_ms` oder `total_ms` |
| Hauptfarbe | `color` |
| zweite gleichwertige Farbe | `secondary_color` |
| konkrete Hintergrundfarbe | `background_color` |
| Segmentbreite | `segment_length` oder ein eindeutig beschriebener lokaler Name |

Wenn `animated=True`, muss `speed` deklariert sein.
Wenn `directional=True`, muss `reverse` deklariert sein.
Event und Timed Overlay benötigen eine endliche Dauer.

Lies für Farbmodelle und Parameter `references/PARAMETERS_AND_COLORS.md`.

### 7. Renderlogik zeitbasiert schreiben

Zeitabhängige Effekte verwenden immer:

```python
elapsed = max(0.0, ctx.now - ctx.invocation.created_at)
```

Berechne daraus Phase, Position oder Fortschritt. Verwende keine internen
Framezähler und keine eigenen Timer.

Der gleiche Zeitpunkt muss bei gleicher Konfiguration denselben Frame liefern.
Die reale Geschwindigkeit darf sich bei einer anderen Render-FPS nicht ändern.

Lies und verwende die Muster aus `references/RENDERING_RECIPES.md`.

### 8. Immer einen vollständigen Frame zurückgeben

Verbindlich:

```python
len(frame) == ctx.led_count
```

- Deckender Effekt: jede Position enthält einen RGB-Integer.
- Transparenter Effekt: unbeteiligte Positionen enthalten `None`.
- `0x000000` ist Schwarz und verdeckt einen darunterliegenden Wert.
- `None` erhält bei transparenter Komposition den darunterliegenden Wert.
- Nie zwölf LEDs fest codieren; immer `ctx.led_count` verwenden.

### 9. Presets kuratieren

Erstelle normalerweise zwei bis vier Presets, die die Bandbreite sinnvoll
zeigen. Presets enthalten ausschließlich deklarierte Konfigurationsparameter.
Sie ändern niemals Typ, Layer, Lebensdauer oder den Definitionvertrag.

Verwende klare Beschreibungen statt automatisch klingender Texte.

### 10. Quelle prüfen

Führe mindestens aus:

```powershell
python .\tools\effect_packager.py validate-effect-source <quelle>
```

Danach bauen und verifizieren:

```powershell
python .\tools\effect_packager.py pack-effect <quelle> <ausgabe.lefx>
python .\tools\effect_packager.py verify-effect-package <ausgabe.lefx>
```

Bei First-Party-Effekten zusätzlich, sofern für den Auftrag vorgesehen:

```powershell
python .\tools\effect_building\build_lefxset.py --rebuild-packages
```

Korrigiere jeden Fehler an der Quelle. Umgehe die Validierung nicht.

### 11. Verhalten gezielt prüfen

Prüfe mindestens:

- Frame direkt am Start,
- Frame zu einem späteren Zeitpunkt,
- minimale und maximale Parameter,
- Ringumbruch,
- `reverse=True`, falls vorhanden,
- exakt `ctx.led_count` Einträge,
- Transparenz oder Deckung wie deklariert,
- Anfang, Mitte und Ende bei endlichen Effekten,
- ungültige Parameter werden vom Schema abgewiesen.

Nutze `references/QUALITY_CHECKLIST.md`.

### 12. Abschlussmeldung

Berichte knapp und vollständig:

1. erstellte oder geänderte Dateien,
2. Typ und sichtbares Verhalten,
3. verfügbare Parameter und Presets,
4. ausgeführte Validierungs-, Build- und Testbefehle,
5. Ergebnis oder noch vorhandener konkreter Fehler.

Behaupte keinen erfolgreichen Test, der nicht ausgeführt wurde.

## Harte Regeln

- Ändere nicht die Engine, um einen einzelnen Effekt möglich zu machen.
- Importiere keine Controller-, Service- oder Registry-Module.
- Importiere keine anderen LEFX-Pakete.
- Erstelle keine gemeinsame `common.py` für mehrere Effekte.
- Verwende nur erlaubte Standardbibliotheken, `src.core.effect_schema`,
  `src.core.color_math` und paketlokale relative Importe.
- Starte keine Threads, Timer oder Nebenprozesse.
- Verwende keine Framezähler als Zeitquelle.
- Implementiere keinen eigenen Start-, Stop-, Reset- oder Finished-Lebenszyklus.
- Parser für Farbnamen, Dauertexte oder Bool-Aliase gehören nicht in `render()`.
  Der Renderer erhält bereits kanonische, validierte Werte.
- Füge keine unnötigen Parameter hinzu.
- Gib keine Teilimplementierung als fertigen Effekt aus.

## Beispiele auswählen

| Aufgabe | Startbeispiel |
|---|---|
| weicher pulsierender Grundzustand | `examples/state_soft_pulse/` |
| rotierendes Segment | `examples/state_rotating_segment/` |
| endlicher transparenter Sweep | `examples/timed_overlay_sweep/` |
| kurzer Helligkeitspuls | `examples/event_short_pulse/` |

Kopiere nur ein Beispiel, wenn es dem gewünschten Lebenszyklus entspricht.
Ändere nicht lediglich Titel und Farben; passe die Renderlogik fachlich an.

## Maßgebliche Projektdokumentation

Bei Widersprüchen oder Anforderungen außerhalb dieses Skills sind die aktuelle
Implementierung und diese Dokumentation maßgeblich:

- `docs/effect-system/03_layers_and_composition.md`
- `docs/effect-system/04_effect_types_and_lifecycles.md`
- `docs/effect-system/05_schema_v2.md`
- `docs/effect-system/06_parameters_and_values.md`
- `docs/effect-system/08_packages_ids_and_configuration.md`
- `docs/effect-system/10_validation_and_build.md`
- `docs/effect-development/README.md`
