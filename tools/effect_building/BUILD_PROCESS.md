# LEFX-V2-Buildprozess

Diese separate Buildstrecke unter `tools/effect_building/` erzeugt die
First-Party-Effektartefakte. Sie ist nicht der EXE-/Release-Build unter
`build-tools/`.

## Autoritative Quellen

Die Quellen liegen ausserhalb von `build/` unter
`tools/effect_building/sources/`. Jedes Set ist ein eigener Ordner mit einem
dauerhaften Manifest:

- `tools/effect_building/sources/default-effects/set.yaml`
- `tools/effect_building/sources/smartspeaker-set/set.yaml`

Die Effektquellen eines Sets liegen in den typisierten Unterordnern:

- `sources/<set-id>/states/<id>/`
- `sources/<set-id>/overlays/<id>/`
- `sources/<set-id>/events/<id>/`

Es gibt keine Python-Registry der Set-Namen: Ein neues Set wird allein durch
`tools/effect_building/sources/<set-id>/set.yaml` bekannt. Die Discovery sucht
ausschliesslich nach `sources/*/set.yaml`, prueft die Ordnerstruktur hart und
bricht bei verwaisten Legacy-Quellen (z. B. `sources/states/...`) ab.

Der komplette Ordner `tools/effect_building/build/` ist generiert und darf
beim Cleanup geloescht werden.

Jeder ID-Ordner ist eine eigenstaendige Paketquelle. Es gibt weder eine
typuebergreifende `common.py` noch Importe aus anderen Definitionen.

## Einzelne LEFX-Pakete bauen

```powershell
python tools/effect_building/build_lefx.py
```

Der Build:

1. entdeckt alle Sets ueber `sources/*/set.yaml`
2. entdeckt und validiert die Effektquellen jedes Sets
3. validiert Quelllayout, Imports und den strikten LEFX-V2-Vertrag
4. baut je Definition genau eine `.lefx`
5. fuehrt je Paket einen Import- und Render-Smoke-Test aus

Die Pakete landen getrennt unter
`build/.cache/build_lefx/<set-id>/*.lefx`. Root-Overrides fuer Tests und
Diagnose: `--sources-root` und `--output-root` (gemeinsamer Package-Cache-Root,
pro Set wird ein Unterordner erzeugt).

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

Der Set-Build arbeitet ausschliesslich aus vorgebauten `.lefx`-Paketen:
Fehlende, zusaetzliche oder fremde Pakete brechen den Build hart ab, und es
entstehen keine Uebergangswarnungen ueber aus Quellordnern gebaute Mitglieder.

Ergebnisse pro Set:

- `build/output/<set-id>.lefxset`
- `build/published/<set-id>.lefxset`

Der temporaere Zwischenstand unter `build/.cache` wird nach einem
erfolgreichen Build automatisch entfernt. `--keep-cache` behaelt ihn gezielt
fuer die Fehlersuche. Die Option `--publish-copy` ist entfallen; die
Veroeffentlichung erfolgt jetzt automatisch fuer alle Sets ueber
`--publish-root`.

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

Der normale Release-Build ruft
`python tools/effect_building/build_lefxset.py --rebuild-packages` auf und
konsumiert alle fertigen `.lefxset`-Artefakte ueber das Output-Verzeichnis in
`build-tools/build_config.json` (`builtin-effects-discovery`).
