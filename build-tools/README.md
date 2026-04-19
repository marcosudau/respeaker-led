# Build Tools

Dieses Verzeichnis enthaelt den kompletten normalen Build-Prozess fuer die Service-EXE und das Release-Bundle.

## Standard-Build

Der Einstieg ist [build.py](build.py).

```powershell
uv run python build-tools/build.py --force
```

Standardmaessig wird mit Versionssuffix gebaut:

- `dist/led_controller_service_<version>.exe`
- `dist/release_bundle/led_controller_service_<version>_windows_x64.zip`

Mit `--no-version` werden die Dateinamen ohne Versionssuffix erzeugt.

`build.py` liest [build_config.json](build_config.json), baut optional zuerst die konfigurierten Effektartefakte, erstellt dann die EXE, prueft sie, erzeugt das Release-Bundle als ZIP, prueft auch dieses und fuehrt am Ende optional das Cleanup aus.

Wichtig:

- Dieser Ablauf ist der normale Service-Build.
- Das eigentliche Effekt-Building liegt separat unter `tools/effect_building/`.
- `build.py` konsumiert nur fertige `.lefx`- und `.lefxset`-Artefakte, die in `builtin-effects-discovery` konfiguriert sind.

## Einzelne Skripte

- [build.py](build.py): Fuehrt den kompletten normalen Build-Pfad am Stueck aus.
- [led_controller_service.spec](led_controller_service.spec): Beschreibt den PyInstaller-Build und bindet die konfigurierten Builtin-Effekte ein.
- [version.py](version.py): Enthaeit die einzige gueltige Versionsquelle fuer Build und Release.
- [scripts/check_exe.py](scripts/check_exe.py): Prueft die gebaute EXE per Smoke-Test.
- [scripts/create_release_bundle.py](scripts/create_release_bundle.py): Baut aus Template, EXE und konfigurierten Effektartefakten das Release-Bundle als ZIP.
- [scripts/check_release_bundle.py](scripts/check_release_bundle.py): Prueft Struktur und Pflichtdateien des erzeugten Release-Bundles.
- [scripts/cleanup_after_build.py](scripts/cleanup_after_build.py): Raeumt Build-Reste weg und laesst standardmaessig nur EXE und Release-Bundle-ZIP uebrig.
- [scripts/cleanup_paths.json](scripts/cleanup_paths.json): Definiert die aufraeumbaren Pfade fuer Default- und Komplett-Cleanup.

## build_config.json

- `spec_file`: Legt den Pfad zur PyInstaller-Spec-Datei fest.
- `build_effects`: Schaltet das vorgeschaltete Effekt-Building ein oder aus.
- `build_exe`: Schaltet den EXE-Build samt EXE-Pruefung ein oder aus.
- `build_release_bundle`: Schaltet den Bundle-Build samt Bundle-Pruefung ein oder aus.
- `cleanup`: Schaltet das Cleanup nach dem Build ein oder aus.
- `builtin-effects-discovery`: Definiert `.lefx`, `.lefxset` oder Ordner, aus denen Builtin-Effekte rekursiv eingesammelt werden.

## Versionierung

Die Version kommt ausschliesslich aus [version.py](version.py).

Lokale Builds lesen die Version nur; sie aendern sie nicht.

Standardmaessig enthalten EXE und Release-Bundle die Versionsnummer im Dateinamen.

Mit `--no-version` werden `led_controller_service.exe` und `led_controller_service_windows_x64.zip` ohne Versionssuffix gebaut.

## Release-Bundle und Template

Das Release-Bundle wird von [scripts/create_release_bundle.py](scripts/create_release_bundle.py) aus [template_release_bundle](template_release_bundle) erzeugt und direkt als ZIP unter `dist/release_bundle/` gespeichert.

Dabei wird das Template zuerst in einen temporaeren Staging-Ordner kopiert, danach wird die gebaute EXE in das Bundle-Root gelegt und die ueber `builtin-effects-discovery` gefundenen `.lefxset`-Dateien nach `effects/` sowie `.lefx`-Dateien nach `packages/` kopiert.

Im Bundle wird zusaetzlich eine `bundle_manifest.json` erzeugt, und `effects/default-effects.lefxset` ist Pflicht.

## Cleanup

Im Default-Modus entfernt [scripts/cleanup_after_build.py](scripts/cleanup_after_build.py) nur Build-Reste wie `build/`, Logs und Staging-Verzeichnisse.

Mit `--complete` werden zusaetzlich auch die gebaute EXE und das Release-Bundle-ZIP geloescht.

Falls [scripts/cleanup_paths.json](scripts/cleanup_paths.json) fehlt, erzeugt das Skript sie mit einer Grundstruktur neu und laeuft weiter.

## Verzeichnisstruktur

`build-tools/`

|-- [_build_common.py](_build_common.py)

|-- [build.py](build.py)

|-- [build_config.json](build_config.json)

|-- [led_controller_service.spec](led_controller_service.spec)

|-- [README.md](README.md)

|-- [RELEASE.md](RELEASE.md)

|-- [version.py](version.py)

|-- scripts/

|   |-- [check_exe.py](scripts/check_exe.py)

|   |-- [check_release_bundle.py](scripts/check_release_bundle.py)

|   |-- [cleanup_after_build.py](scripts/cleanup_after_build.py)

|   |-- [cleanup_paths.json](scripts/cleanup_paths.json)

|   `-- [create_release_bundle.py](scripts/create_release_bundle.py)

`-- template_release_bundle/

    |-- [README.md](template_release_bundle/README.md)

    |-- docs/

    |   |-- [HOST_APP_INTEGRATION.md](template_release_bundle/docs/HOST_APP_INTEGRATION.md)

    |   `-- [REFERENCE.md](template_release_bundle/docs/REFERENCE.md)

    `-- examples/

        |-- [example_usage.py](template_release_bundle/examples/example_usage.py)

        `-- [led_controller_host.py](template_release_bundle/examples/led_controller_host.py)
