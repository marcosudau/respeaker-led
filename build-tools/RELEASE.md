# Release Guide

Diese Datei beschreibt den aktuellen Release-Ablauf fuer den normalen Build-Pfad.

## Versionsquelle

Die einzige gueltige Versionsquelle ist [version.py](version.py).

Lokale Builds lesen diese Version nur; sie aendern sie nicht.

Wenn die Version angepasst wird, muss auf GitHub auch ein passender Tag `vX.Y.Z` erzeugt werden.

## Lokaler Release-Build

Der komplette lokale Release-Build laeuft ueber [build.py](build.py).

```powershell
uv run python build-tools/build.py --force
```

Standardmaessig entstehen dabei:

- `dist/led_controller_service_<version>.exe`
- `dist/release_bundle/led_controller_service_<version>_windows_x64.zip`

Mit `--no-version` werden die Dateinamen ohne Versionssuffix erzeugt.

## GitHub Release

Der GitHub-Release-Workflow startet auf Tags im Format `v*`.

Vor dem Release prueft der Workflow, dass der Tag exakt zur Version in [version.py](version.py) passt.

Danach laufen:

1. Tests
2. normaler Build ueber `build-tools/build.py`
3. Ermittlung des erzeugten ZIP-Bundles aus `dist/release_bundle/`
4. Changelog-Erzeugung aus den Commits seit dem letzten Tag
5. GitHub-Release mit Bundle-ZIP und `CHANGELOG.md`

## Release-Bundle

Das Release-Bundle wird aus [template_release_bundle](template_release_bundle) gebaut und als ZIP veroeffentlicht.

Es enthaelt die gebaute EXE im Bundle-Root, die eingebundenen Builtin-Effektdateien unter `effects/` und `packages/` sowie die statischen Doku- und Beispiel-Dateien aus dem Template.

Das separate Effekt-Building ist nicht dieser Release-Ablauf selbst. Der normale Release-Build konsumiert nur die ueber [build_config.json](build_config.json) konfigurierten Effekt-Artefakte.
