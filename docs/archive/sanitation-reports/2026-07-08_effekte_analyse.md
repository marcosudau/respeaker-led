# Bericht 2: Effektlogik, Effektdefinitionen und LEFX/LEFXSET-System

Stand: 2026-07-08  
Untersuchter Arbeitsbaum: `C:\Users\marco\OneDrive\Desktop\Respeaker_MaterialCheck\led_controller_respeaker`

## Kurzfazit

Die Trennung der Effektdefinitionen von der eigentlichen Controller-Logik ist in dieser Version weitgehend umgesetzt. Die fachlichen Effektdefinitionen liegen nicht mehr im aktiven Runtime-Pfad unter `src/`, sondern im separaten Effekt-Building unter `tools/effect_building/effect_definitions/`. Die Runtime laedt die Standardbibliothek als gebautes `default-effects.lefxset`.

Die Runtime kennt weiterhin das abstrakte Effektmodell (`BaseEffect`, `EffectDefinition`, `LayerRule`, `RenderContext`) und die Paketloader/-builder. Sie enthaelt aber keine konkrete Standard-Effektbibliothek mehr. Das ist eine echte, technisch wirksame Trennung.

## Grundmodell

Ein Effekt ist in diesem System eine Python-Klasse, die von `BaseEffect` erbt und zwei Dinge liefert:

- `definition`: Metadaten, Parameter, Defaults, Capabilities und Layerregeln.
- `render(ctx)`: eine Liste von 12 Farben oder `None`-Werten.

`None` bedeutet transparent. Ein Integer bedeutet konkrete RGB-Farbe. Die Runtime rendert nicht direkt einen Effektnamen, sondern arbeitet mit `EffectInvocation` und `RenderContext`.

Die wichtigsten Vertrage liegen in:

- `src/core/effect_schema.py`
- `src/engine/effect_registry.py`
- `src/engine/effect_package_schema.py`
- `src/engine/effect_package_loader.py`
- `src/engine/effect_package_builder.py`

## Wo die Effektdefinitionen liegen

Die gepflegten Standard-Effektquellen liegen hier:

```text
tools/effect_building/effect_definitions/
```

Relevante Dateien:

- `basic.py`: Basis- und State-Effekte wie `off`, `solid_color`, `soft_pulse`, `blink_color`, `progress_bar`.
- `overlays.py`: Spezial-Overlays wie `direction_indicator`, `countdown_ring`, `warning_flash`.
- `ring_effects.py`: umfangreiche Ring-, Segment-, Dot-, Flash-, Pulse- und DoA-Effekte.
- `common.py`: gemeinsame Parser, Farb-/Parameter-Helfer und Standard-Layerregeln.

`tools/effect_building/standard_effects.py` entdeckt diese Klassen, generiert daraus Effektquellen, Presets und Commands und baut daraus `.lefx`-Pakete sowie ein `.lefxset`.

## Artefaktmodell

Es gibt zwei zentrale Artefakttypen:

- `.lefx`: ein einzelnes Effektpaket.
- `.lefxset`: ein Set aus mehreren `.lefx`-Paketen.

Ein `.lefx` enthaelt:

- `manifest.json`
- `hashes.json`
- `payload/` mit der Effektklasse und Abhaengigkeiten
- optional `effect-presets.json`
- optional `commands.json`
- optional Assets/Extra-Dateien

Ein `.lefxset` enthaelt:

- `set-manifest.json`
- `hashes.json`
- mehrere verschachtelte `.lefx`-Dateien unter `effects/`

Die Loader pruefen SHA-256-Hashes, Manifest-Struktur, Entry-Class, `BaseEffect`-Subclassing und ob Manifest und Klassendefinition zueinander passen.

## Build-Strecke fuer Effekte

Die separate Effekt-Build-Strecke liegt unter:

```text
tools/effect_building/
```

Wichtige Skripte:

- `build_lefx.py`: baut einzelne `.lefx`-Pakete fuer die Standard-Effekte.
- `build_lefxset.py`: buendelt `.lefx`-Pakete zum `default-effects.lefxset`.
- `standard_effects.py`: Discovery, Quellen-Generierung, Preset-/Command-Erzeugung, Smoke-Render.
- `BUILD_PROCESS.md`: beschreibt den Ablauf.

Ausgabeorte:

- Quellen: `tools/effect_building/build/sources/default-effects`
- Einzelpakete: `tools/effect_building/build/build_lefx/default-effects`
- Set: `tools/effect_building/build/build_lefxset/default-effects.lefxset`
- Publish-Kopie: `tools/effect_building/build/published/default-effects.lefxset`

Das normale Release-Building unter `build-tools/` konsumiert diese Artefakte ueber `build-tools/build_config.json`. Es ist nicht der Ort, an dem die Effektlogik selbst definiert wird.

## Runtime-Laden der Effekte

Die Default-Registry wird in `src/engine/effect_registry.py` gebaut. Der Ablauf:

1. Registry startet leer.
2. Es wird zuerst nach `effects/default-effects.lefxset` neben der App/EXE gesucht.
3. In der Entwicklung werden zusaetzlich die Pfade aus `build-tools/build_config.json` beruecksichtigt.
4. Das `default-effects.lefxset` wird als Quelle `default-effects` geladen.
5. Weitere `.lefx`/`.lefxset`-Quellen koennen aus `packages/` autodiscovered oder per API/CLI registriert werden.

Die Registry verwaltet:

- registrierte Effektklassen;
- Source-IDs;
- Paket-/Set-Metadaten;
- Presets;
- Commands;
- Alias-Aufloesung fuer `default-effects::effect_id` vs. lokale IDs.

Wichtig: Fuer die Default-Quelle werden lokale IDs wie `solid_color` weiterhin akzeptiert. Zusaetzliche Quellen werden qualifiziert als `source_id::effect_id`.

## Aktuell verifizierte Standard-Effekte

Die aktuelle Standardbibliothek enthaelt 37 Effekte:

- `blink_color`
- `blink_impulse`
- `blink_pattern`
- `chase_dot`
- `countdown_ring`
- `countdown_segment`
- `direction_indicator`
- `doa_direction_dot`
- `doa_direction_segment`
- `double_flash`
- `fading_rotating_segment`
- `fill_ring`
- `highlighted_segment`
- `off`
- `opposing_markers`
- `progress_bar`
- `progress_ring`
- `pulse_pattern`
- `radar_sweep`
- `rotating_gap`
- `rotating_gradient`
- `rotating_segment`
- `scanner`
- `short_flash`
- `short_ping`
- `short_pulse`
- `short_running_dot`
- `short_soft_pulse`
- `short_sweep`
- `soft_pulse`
- `soft_pulsing_ring`
- `solid_color`
- `sparkle_burst`
- `timer_ring`
- `triple_flash`
- `warning_flash`
- `yin_yang_spin`

Die Runtime-Registry meldet dazu:

- 37 Effekte
- 148 Presets
- 148 Commands

Das passt zum Generator in `standard_effects.py`, der pro Standard-Effekt mehrere Presets und dazu passende Commands erzeugt.

## Presets und Commands

Presets liegen logisch zwischen Effektdefinition und Bedienoberflaeche/API. Ein Preset definiert:

- Kategorie: `state`, `effect`, `overlay` oder `event`;
- Ziel-Layer;
- Parameter;
- optional Dauer, Prioritaet, Queue-Verhalten und Tags.

Commands sind bedienbare Aktionen aus den Paketen:

- `state_toggle`: braucht `on` und `off`.
- `event`: darf nur `on` haben.

Commands koennen entweder:

- ein Preset anwenden;
- einen Effekt direkt anwenden;
- einen Layer leeren.

Die Parser validieren, dass Kategorien, Layer, Presetnamen und Effekt-Referenzen zusammenpassen. Innerhalb eines Sets werden doppelte Preset-IDs und Command-Namen verhindert.

## Layerregeln und Abspielmodi

Ein Effekt darf nicht automatisch auf jedem Layer laufen. Die `LayerRule` entscheidet:

- ob ein Layer erlaubt ist;
- welche Playback-Modes erlaubt sind;
- ob finite oder indefinite Duration erforderlich ist;
- ob Transparenz erlaubt ist;
- ob Queuing erlaubt ist;
- ob Background-Persistenz erlaubt ist.

Typische Muster:

- State-/Background-Effekte sind persistent oder loopfaehig.
- Event-Effekte sind single-run und brauchen eine finite Dauer.
- Overlays koennen transparent sein.
- `BACKGROUND_STATE_LAYER` kann persistierbar sein.

Diese Regeln sind der wichtigste Schutz gegen fachlich falsche Effektanwendung.

## Wie stark ist die Trennung wirklich?

Die Trennung ist stark, aber nicht absolut.

Was sauber getrennt ist:

- Konkrete Standard-Effektdefinitionen liegen unter `tools/effect_building/effect_definitions/`.
- Die Runtime laedt Default-Effekte aus `.lefxset`, nicht aus rohen Standard-Effektquellen.
- Das normale Build-System konsumiert Effektartefakte ueber Konfiguration.
- Zusaetzliche Effekte werden als Artefakte registriert oder autodiscovered.
- Presets und Commands reisen mit dem Effektpaket.

Was bewusst gemeinsam bleibt:

- `BaseEffect`, `EffectDefinition`, `LayerRule`, `RenderContext` liegen in `src/core/effect_schema.py`, weil Runtime und Effektpakete denselben Vertrag brauchen.
- Loader, Builder, Registry und Schema liegen unter `src/engine`, weil sie Teil der Produktfaehigkeit sind.
- Die Runtime kennt weiterhin konkrete Default-Effekt-IDs in der Normalisierung, z. B. `solid_color`, `soft_pulse`, `blink_color`, `direction_indicator`, `countdown_ring`, `progress_bar`, `warning_flash`.

Der letzte Punkt ist der wichtigste Rest-Coupling-Befund: Die Effektimplementierung ist getrennt, aber die Hauptlogik codiert noch fachliche Default-Effekt-IDs in `ControllerCommandNormalizer`. Wenn ein Default-Effekt umbenannt oder entfernt wird, bricht die Hauptlogik. Das ist wahrscheinlich akzeptabel fuer eine eingebaute Standardbibliothek, aber nicht vollstaendig datengetrieben.

## Risiken und Inkonsistenzen im Effektteil

1. Die Runtime haengt fuer Standardzustaende an festen Effekt-IDs.
   - Beispiel: `set_state("recording")` erwartet `soft_pulse`.
   - Beispiel: Countdown erwartet `countdown_ring`.
   - Das ist kein Packaging-Fehler, aber eine Architekturgrenze.

2. Generierte Quellen und gebaute Artefakte liegen im Repo-Arbeitsbaum.
   - Das ist praktisch fuer Entwicklung, kann aber zu Verwirrung fuehren: Quellwahrheit ist `effect_definitions`, Laufzeitwahrheit ist das gebaute `.lefxset`.

3. `build_config.json` verweist auf mehrere Discovery-Pfade.
   - Der Registry-Code versucht Duplikate zu erkennen und zu ueberspringen.
   - Funktional scheint das aktuell zu funktionieren, ist aber kognitiv schwerer als ein einzelner eindeutig publizierter Pfad.

4. Effektpakete fuehren Python-Code aus.
   - Das ist fuer lokale eigene Pakete normal, aber keine Sandbox. Fremde `.lefx`-Artefakte waeren sicherheitstechnisch Code-Ausfuehrung.

5. `zipfile.extractall` wird fuer Paketextraktion verwendet.
   - Bei untrusted Artefakten waere Pfadvalidierung gegen Zip-Slip sinnvoll. Im aktuellen lokalen Build-/Eigenartefakt-Modell ist das Risiko geringer, aber architektonisch vorhanden.

## Validierung

Ausgefuehrte Pruefungen:

```text
uv run python tools/effect_packager.py verify-effect-package tools\effect_building\build\build_lefxset\default-effects.lefxset
```

Ergebnis: erfolgreich. Das Paket wurde als `effect_set` mit `source_id = default-effects` und `set_id = default-effects` verifiziert.

Runtime-Registry per `build_default_effect_registry()`:

```text
EFFECTS 37
PRESETS 148
COMMANDS 148
```

Gesamttests:

```text
uv run pytest -q --basetemp=.pytest_tmp
```

Ergebnis:

```text
115 passed, 1 failed
```

Der Fehlschlag betrifft Release-Tooling, nicht direkt die Effektlogik:

```text
tests/test_release_tooling.py::test_create_release_bundle_replaces_existing_zip_without_force
```

Die Effekt-Paketvalidierung selbst war erfolgreich.

## Gesamt-Einschaetzung

Der Effektteil ist der am weitesten modularisierte Teil dieses Projekts. Das Ziel, Effektdefinitionen von der eigentlichen Controller-Logik zu trennen, ist in dieser Version ueberwiegend erreicht. Besonders stark ist, dass Effekte nicht nur in andere Python-Dateien verschoben wurden, sondern als versionierte Artefakte mit Manifest, Hashes, Presets und Commands gebaut und geladen werden.

Die Architektur ist fuer lokale, eigene Effektpakete gut geeignet. Sie erlaubt neue Effekte, ohne den Service-Code selbst zu erweitern, solange sie dem `BaseEffect`-Vertrag folgen. Die Tests und Smoke-Render im Build-Prozess stuetzen dieses Modell.

Der wichtigste Verbesserungsbereich ist die verbleibende Kopplung zwischen Controller-Normalizer und festen Default-Effekt-IDs. Eine naechste Ausbaustufe waere, Standard-State-Mappings datengetrieben aus einem Default-Preset-/Command-Manifest zu laden, statt `solid_color`, `soft_pulse`, `blink_color` usw. im Normalizer hart zu codieren. Fuer den aktuellen Stand ist das aber kein akuter Defekt, sondern eine klare Architekturgrenze.
