# LEFX-V2-Buildprozess

Diese separate Buildstrecke unter `tools/effect_building/` erzeugt die
Standard-Effektartefakte. Sie ist nicht der EXE-/Release-Build unter
`build-tools/`.

## Autoritative Quellen

Die Quellen liegen ausserhalb von `build/`:

- `tools/effect_building/sources/states/<id>/`
- `tools/effect_building/sources/overlays/<id>/`
- `tools/effect_building/sources/events/<id>/`
- `tools/effect_building/standard_effects.py`

Der komplette Ordner `tools/effect_building/build/` ist generiert und darf
beim Cleanup geloescht werden.

Jeder ID-Ordner ist eine eigenstaendige Paketquelle. Es gibt weder eine
typuebergreifende `common.py` noch Importe aus anderen Definitionen.

## Einzelne LEFX-Pakete bauen

```powershell
python tools/effect_building/build_lefx.py
```

Der Build:

1. entdeckt die typisierten Quellen rekursiv
2. validiert Quelllayout, Imports und den strikten LEFX-V2-Vertrag
3. baut je Definition genau eine `.lefx`
4. fuehrt je Paket einen Import- und Render-Smoke-Test aus

Eine Paketquelle enthaelt:

- `effect.yaml`
- `effect.py`
- optional `presets.yaml`
- lokale Python-Abhaengigkeiten
- optional `assets/` und `extra/`

`commands.json` ist in V2 nicht erlaubt. Presets enthalten ausschliesslich
Konfigurationswerte und koennen Typ, Layer, Laufzeit oder Queue-Verhalten
nicht ueberschreiben.

## LEFXSET bauen

```powershell
python tools/effect_building/build_lefxset.py
```

Oder einschliesslich Neubau der Einzelpakete:

```powershell
python tools/effect_building/build_lefxset.py --rebuild-packages
```

Ergebnisse:

- `build/output/default-effects.lefxset`
- `build/published/default-effects.lefxset`

Der temporaere Zwischenstand unter `build/.cache` wird nach einem
erfolgreichen Standard-Build automatisch entfernt. `--keep-cache` behaelt ihn
gezielt fuer die Fehlersuche.

## V2-Vertragsregeln

- Paketformat: `lefx/2`
- Setformat: `lefxset/2`
- genau eine State-, Overlay- oder Event-Definition pro `.lefx`
- Quellordner und deklarierter Definitionstyp muessen uebereinstimmen
- endliche Definitionen deklarieren ihre Dauer
- Runtime-Eingaben sind nur bei kontrollierten Overlays erlaubt
- kontrollierte Overlays deklarieren Push- oder Pull-Abtastung
- Standard-Heartbeat: 1000 ms, Fehler nach drei verpassten Zeitfenstern
- bis zum Fehler bleibt der letzte gueltige Wert aktiv; danach erhaelt die
  Renderlogik fuer betroffene Eingaben `None`
- Effektlogik und benoetigte Hilfsmodule befinden sich im Paket
- kein `common.py`, kein Import aus Controller-, Service- oder Registry-Code
- unbekannte Manifestfelder brechen den Build ab

Der normale Release-Build konsumiert nur fertige `.lefx`- und
`.lefxset`-Artefakte ueber `build-tools/build_config.json`.
