# Effekte Verstehen Und Neue Effekte Erstellen

Diese Seite beschreibt das heutige Effektmodell des Service und vor allem die Trennung zwischen Runtime, normalem Build und separatem Effekt-Building.

## Die kurze Version

Ein Effekt ist fachlich eine Effektdefinition mit Parametern, Layerregeln und Renderlogik.

Fuer den laufenden Service wichtig ist heute aber vor allem:

- der Service laedt Effekte nicht aus rohen Python-Quellen in `src/`
- der Service arbeitet mit `.lefx`- und `.lefxset`-Artefakten
- das normale Building unter `build-tools/` konsumiert diese Artefakte nur
- das eigentliche Effekt-Building lebt separat unter `tools/effect_building/`

## Wichtige Trennung

Damit keine Verwechslung entsteht:

- `build-tools/` ist fuer EXE und Release-Bundle zustaendig
- `tools/effect_building/` ist fuer das Erzeugen der Effekt-Artefakte zustaendig
- `src/` enthaelt Runtime, Registry, Loader und die Service-Logik

Wenn du also "Effekte bauen" meinst, ist das nicht der normale EXE-Build.

## Welche Effektdateien der Service heute wirklich verwendet

Der Service arbeitet mit zwei Artefakttypen:

- `.lefx` fuer einzelne Effektpakete
- `.lefxset` fuer Effektsets

Fuer den normalen Build sind diese Quellen relevant:

- die in `build-tools/build_config.json` eingetragenen Pfade unter `builtin-effects-discovery`
- im Release-Bundle `effects/default-effects.lefxset`
- zusaetzliche Laufzeit-Artefakte unter `packages/` neben der EXE

Das bedeutet:

- `build-tools/build_config.json` ist die massgebliche Builtin-Konfiguration
- `effects/default-effects.lefxset` ist im Bundle Pflicht
- weitere `.lefx`- oder `.lefxset`-Dateien koennen zusaetzlich registriert oder autodiscovered werden

## Wie der Service Effekte laedt

Beim Aufbau der Default-Registry passiert heute vereinfacht:

1. Die Runtime baut eine leere Registry auf.
2. Im Bundle wird zuerst `effects/default-effects.lefxset` neben der EXE gesucht.
3. Zusaetzlich kennt die Runtime die ueber `build-tools/build_config.json` konfigurierten Builtin-Artefakte.
4. Das Effektset wird als Quelle `default-effects` geladen.
5. Weitere `.lefx`- und `.lefxset`-Artefakte koennen aus `packages/` autodiscovered oder ueber CLI/API registriert werden.

## Konsequenzen fuer die Arbeit an Effekten

- Eine neue Python-Buildquelle allein macht einen Effekt noch nicht im Service sichtbar.
- Der Effekt muss im separaten Effekt-Building aufgenommen und zu `.lefx` oder `.lefxset` gebaut werden.
- Erst das gebaute Artefakt kann durch den normalen Build oder zur Laufzeit eingebunden werden.
- Doppelte Effekt-IDs verhindern Build, Start oder Reload klar und frueh.

## Was beim Effekt-Building typischerweise geaendert wird

Das Effekt-Building liegt unter `tools/effect_building/`.

Dort liegen heute die wichtigsten Bausteine:

- `build_lefx.py`
- `build_lefxset.py`
- `standard_effects.py`

Wenn du einen vorhandenen Effekt weiterentwickelst oder einen neuen Effekt hinzufuegst, passiert die eigentliche Aenderung dort und nicht im normalen Build unter `build-tools/`.

## Typischer Ablauf fuer neue oder geaenderte Effekte

1. Die Buildquelle im separaten Effekt-Building anpassen.
2. Das passende Effekt-Build-Skript unter `tools/effect_building/` ausfuehren.
3. Den Service neu starten oder `reload-effect-sources` verwenden.
4. Mit `list-effects` und `apply-effect` pruefen, ob der Effekt wie erwartet registriert ist.

Beispiel fuer die Sichtpruefung:

```powershell
python .\main.py list-effect-sources
python .\main.py list-effects
```

Dann ein direkter Test:

```powershell
python .\main.py apply-effect solid_color main --params '{"color":"0x224466"}'
python .\main.py apply-effect soft_pulse state --params '{"color":"0x33AAFF","background_color":"0x02060A","period_ms":1600}'
```

## Was die Runtime an einem Effekt benoetigt

Ein registrierter Effekt bringt mindestens diese Informationen mit:

- eine stabile `id`
- Metadaten wie Titel und Beschreibung
- Parameterschema und Defaults
- Layerregeln
- Renderverhalten

Diese Informationen siehst du indirekt auch ueber:

```powershell
python .\main.py list-effects
```

## Praktische Regeln

- keine doppelten IDs verwenden
- Effektlogik nicht in den Runtime-Code unter `src/` mischen
- Effect-Building und normalen Build gedanklich getrennt halten
- Builtins nicht stillschweigend an irgendeinem Pfad ablegen, sondern ueber `build-tools/build_config.json` einbinden

## Beziehung zu Presets

Ein einzelner Effekt ist die technische Basiseinheit.

Ein Preset ist eine hoehere Schicht, die:

- einen oder mehrere Effekte kombiniert
- Parameter vorbelegt
- als wiederverwendbarer Einstiegspunkt fuer CLI oder API dient

Wenn du nur eine neue Visualisierung brauchst, beginne heute mit einer Buildquelle im separaten Effekt-Building.

## Weiterfuehrende Seiten

- [Schnellstart](getting_started.md)
- [CLI und API](api_guide.md)
- [Aktueller Ansatz im Repo](current_approach.md)
- [Effekt-Presets und Commands](presets.md)
- [Entwickler-Einstiege](dev/index.md)
