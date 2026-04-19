# LEFX Build Process

Diese Build-Strecke gehoert zum separaten Effekt-Building unter `tools/effect_building/`.

Sie ist nicht identisch mit dem normalen EXE-/Release-Build unter `build-tools/`.

Die Build-Strecke erzeugt zuerst eigenstaendige `.lefx`-Artefakte fuer alle Standard-Effekte und baut daraus anschliessend die `default-effects.lefxset`.

## Voraussetzungen

- Im Projektwurzelverzeichnis ausfuehren.
- Die Build-Skripte benutzen nur Projektcode und die eingebaute einfache YAML-Verarbeitung.

## 1. LEFX-Pakete erzeugen

```powershell
python tools/effect_building/build_lefx.py
```

Ergebnis:

- Effektquellen werden unter `tools/effect_building/build/sources/default-effects` neu erzeugt.
- Fertige `.lefx`-Dateien landen unter `tools/effect_building/build/build_lefx/default-effects`.
- Jeder Build fuehrt direkt einen Import- und Render-Smoke-Test ueber das gebaute Paket aus.

## 2. LEFXSET erzeugen

```powershell
python tools/effect_building/build_lefxset.py
```

Ergebnis:

- Die `.lefx`-Dateien aus `tools/effect_building/build/build_lefx/default-effects` werden zu `tools/effect_building/build/build_lefxset/default-effects.lefxset` gebuendelt.
- Nach erfolgreichem Build wird die Datei zusaetzlich nach `tools/effect_building/build/published/default-effects.lefxset` kopiert.

Der normale Build konsumiert dieses Effektset nicht ueber einen harten `src/`-Pfad, sondern ueber die in `build-tools/build_config.json` konfigurierte Builtin-Discovery.

Optional kann der zweite Schritt die .lefx-Dateien direkt vorher neu bauen:

```powershell
python tools/effect_building/build_lefxset.py --rebuild-packages
```

## Inhalt der generierten Effektquellen

Jede erzeugte Effektquelle enthaelt:

- effect.yaml
- presets.yaml
- commands.json
- effect.py
- ggf. weitere Python-Abhaengigkeiten wie common.py oder basic.py
- assets/
- extra/

Damit ist jedes gebaute .lefx in sich geschlossen und enthaelt die Effektlogik lokal im Paket.

## Presets und Commands

- Jeder Standard-Effekt bekommt mindestens vier eingebettete Presets.
- State-faehige Effekte erhalten zwei state-Presets plus zwei weitere gueltige Presets.
- Overlay- oder event-only Effekte erhalten vier gueltige Presets innerhalb ihrer erlaubten Kategorien.
- Zu jedem Preset wird ein zugehoeriger Command erzeugt.

## Wichtige Ausgabeorte

- Quellen: `tools/effect_building/build/sources/default-effects`
- Einzelpakete: `tools/effect_building/build/build_lefx/default-effects`
- Set: `tools/effect_building/build/build_lefxset/default-effects.lefxset`
- Publish-Kopie: `tools/effect_building/build/published/default-effects.lefxset`
