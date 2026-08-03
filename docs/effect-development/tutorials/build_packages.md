# Tutorial-Abschluss: LEFX und LEFXSET bauen

Dieser Schritt verwendet die drei Quellen unter `docs/effect_examples`.
Ausgaben gehoeren in einen temporaeren Cache und nicht in den Projektroot.

## 1. Anatomie pruefen

Fuer jede Quelle:

- `effect.yaml` enthaelt eindeutige `package_id`, gemeinsame `source_id` und
  die existierende `entry_class`.
- `effect.py` enthaelt genau eine lokale `BaseEffect`-Unterklasse.
- `presets.yaml` enthaelt nur Konfiguration derselben Definition.
- Typ, Overlay-Modus, Layer, Dauer und Input-Schema sind konsistent.
- Keine `common.py`, Controller-Imports oder Verweise auf andere LEFX-Pakete.

Fuer das Set:

- alle Mitglieder wurden zuerst als `.lefx` gebaut,
- alle besitzen dieselbe `source_id`,
- `set.yaml` nennt genau die vorhandenen LEFX-Dateien,
- Definition- und Preset-IDs kollidieren nicht.

## 2. Drei LEFX-Dateien bauen

```powershell
$out = ".\docs\examples\effects\.cache\tutorial-build"
New-Item -ItemType Directory -Force "$out\set-source\effects" | Out-Null

python .\tools\effect_packager.py pack-effect `
  .\docs\examples\effects\states\example_rotation `
  "$out\set-source\effects\example_rotation_state.lefx"
python .\tools\effect_packager.py pack-effect `
  .\docs\examples\effects\overlays\example_doa `
  "$out\set-source\effects\example_doa_overlay.lefx"
python .\tools\effect_packager.py pack-effect `
  .\docs\examples\effects\events\example_short_pulse `
  "$out\set-source\effects\example_short_pulse_event.lefx"
```

Verifiziere jedes Artefakt mit `verify-effect-package`.

## 3. LEFXSET bauen

Kopiere `docs/effect_examples/tutorial_set/set.yaml` nach
`$out/set-source/set.yaml`. Danach:

```powershell
python .\tools\effect_packager.py validate-effect-set-source "$out\set-source"
python .\tools\effect_packager.py pack-effect-set `
  "$out\set-source" "$out\tutorial-effects.lefxset"
python .\tools\effect_packager.py verify-effect-package `
  "$out\tutorial-effects.lefxset"
```

Das LEFXSET ist das technische Ergebnis der Tutorial-Reihe, bleibt aber ein
lokales Lernartefakt. Nach der Pruefung kann der gesamte Cache entfernt werden:

```powershell
Remove-Item -Recurse -Force .\docs\examples\effects\.cache
```
