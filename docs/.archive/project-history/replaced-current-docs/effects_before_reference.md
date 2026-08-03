# States, Overlays und Events erstellen

Diese Seite beschreibt das LEFX-V2-Modell und die Trennung zwischen
Effektquellen, Artefakten und Controller-Runtime.

Fuer einen gefuehrten Einstieg mit validierbaren Templates, drei vollstaendigen
Beispielen und einem LEFXSET-Abschluss siehe
[Einstieg in die LEFX-V2-Entwicklung](effect-development/README.md).

## Die drei Typen

- **State**: laeuft unbestimmt und belegt den Background- oder Primary-Slot.
- **Overlay**: ist entweder kontrolliert und aktualisierbar oder zeitbegrenzt.
- **Event**: ist kurz, endlich und wird priorisiert in einer Queue abgespielt.

Ein `.lefx` enthaelt genau eine Definition eines dieser Typen. Der Typ
bestimmt den Lebenszyklus und die internen Layer. Aufrufer waehlen keinen
beliebigen Layer.

## Artefakte und Builds

- `.lefx`: ein State, Overlay oder Event
- `.lefxset`: Sammlung mehrerer `.lefx`
- `tools/effect_building/`: Quellen und Effekt-Build
- `build-tools/`: EXE- und Release-Build, konsumiert fertige Artefakte
- `src/`: generische Runtime, Registry, Loader und Renderer

Autoritative Effektquellen liegen unter
`tools/effect_building/sources/states/`,
`tools/effect_building/sources/overlays/` und
`tools/effect_building/sources/events/`, nicht unter `build/`.
`tools/effect_building/build/` enthaelt ausschliesslich generierte Daten.

## Inhalt einer Definition

Eine Definition enthaelt:

- global eindeutige lokale `id`
- `type`: `state`, `overlay` oder `event`
- Metadaten
- strikt typisierte Konfigurationsparameter
- bei kontrollierten Overlays optional Runtime-Eingaben
- Farbmodell und Kompositionsmodus
- Animations- und Richtungsmerkmale
- bei Runtime-Eingaben Push-/Pull-Abtastung und Heartbeat-Regeln
- Lebenszyklusangaben
- lokale Renderlogik und benoetigte Hilfsmodule

`config` ist stabil fuer eine Instanz. `inputs` sind veraenderliche Werte wie
Richtung oder Fortschritt. Runtime-Eingaben sind nur bei kontrollierten
Overlays erlaubt.

## Verbindliche Parametersemantik

- `brightness`: bei visuellen Farbmodellen immer `0.0` bis `1.0`
- `speed`: bei animierten Definitionen ein Multiplikator, Standard `1.0`
- `reverse`: bei gerichteten Definitionen ein Boolean
- `direction_deg`: Winkel in Grad
- `progress`: Fortschritt von `0.0` bis `100.0`
- `color`: kanonische Hauptfarbe
- `secondary_color`: zweite Farbe beim Modell `dual`
- `colors`: Farbliste beim Modell `palette`
- `gradient`: geordnete Farbstopps von Position `0.0` bis `1.0`
- `color_range`: begrenzter HSV-Bereich fuer Zufallsfarben

Alte, explizit deklarierte Aliase wie `value` oder `direction` werden am
Systemrand kanonisiert. Renderlogik sieht nur die kanonischen Namen.

## Kontrollierte Overlay-Eingaben

`push` bedeutet, dass ein Aufrufer Werte oder ein leeres Lebenszeichen an den
Channel sendet. `pull` bedeutet, dass die Paketinstanz ueber `sample_inputs`
Werte im deklarierten Intervall liefert. `interval_ms: 0` erlaubt eine
Abfrage pro Frame.

Der Standard-Heartbeat betraegt eine Sekunde. Nach drei verpassten
Zeitfenstern gilt die Eingabe als fehlerhaft. Bis dahin rendert die Engine mit
dem letzten gueltigen Wert weiter; danach uebergibt sie `None`. Wie `None`
visuell dargestellt wird, entscheidet die Definition selbst. Ein leeres
Push-Update aktualisiert nur das Lebenszeichen und behaelt die letzten Werte.

## Presets

Ein Preset referenziert genau eine Definition und enthaelt nur
Konfigurationswerte. Es darf Typ, Layer, Dauer, Queue-Verhalten oder
Runtime-Eingaben nicht veraendern. Eingebettete Commands gibt es in V2 nicht.

## Standardartefakte bauen

```powershell
python .\tools\effect_building\build_lefx.py
python .\tools\effect_building\build_lefxset.py
```

Oder in einem Schritt:

```powershell
python .\tools\effect_building\build_lefxset.py --rebuild-packages
```

Jedes Paket wird beim Build importiert, validiert und probeweise gerendert.
Unbekannte Manifestfelder, falsche Typvertraege oder doppelte IDs brechen
frueh ab.

## Im Service pruefen

Nach Neustart oder `reload-effect-sources`:

```powershell
python .\main.py list states
python .\main.py list overlays
python .\main.py list events
python .\main.py show <id>
```

Anschliessend passend zum Typ testen:

```powershell
python .\main.py set state <id> --config '{}'
python .\main.py set overlay <id> --channel test --config '{}' --inputs '{}'
python .\main.py emit event <id> --config '{}'
```

Ein zeitbegrenztes Overlay benoetigt keinen Channel. Ein kontrolliertes
Overlay benoetigt einen Channel.

## Praktische Regeln

- fachliche Effektlogik bleibt im Paket
- jede Definition ist eine autarke Quelle ohne geteiltes `common.py`
- anwendungsspezifische Zuordnung bleibt unter `src/integrations/`
- Controller und API interpretieren keine Effektbedeutung
- lokale Definition- und Preset-IDs bleiben global eindeutig
- Farbwerte und andere Parameter werden gegen das deklarierte Schema validiert
- `build/` darf jederzeit komplett neu erzeugt werden

## Weiterfuehrend

- [LEFX-V2-Buildprozess](../tools/effect_building/BUILD_PROCESS.md)
- [LEFX-Schema V2](planning/lefx_schema_v2.md)
- [Presets](presets.md)
- [Runtime-Layer](dev/runtime_layers.md)
