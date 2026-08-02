# Pakete, IDs und Konfiguration

LEFX trennt bearbeitbare Quellen, gebaute Pakete, frei gesetzte Werte und
optionale Konfigurationsvorschlaege.

## Quelle und Paket

```text
Quellverzeichnis -> Build und Validierung -> definition.lefx
```

Ein LEFX-Paket enthaelt genau eine Definition samt Renderlogik, Schemas,
Metadaten, lokalen Abhaengigkeiten und optionalen Presets.

## Anatomie einer LEFX-Quelle

```text
my_effect/
|-- effect.yaml
|-- effect.py
|-- presets.yaml       optional
|-- assets/            optional
`-- extra/             optional
```

`effect.json` kann anstelle von `effect.yaml` verwendet werden. Das
Quellmanifest akzeptiert:

| Feld | Pflicht | Standard / Bedeutung |
|---|---:|---|
| `source_id` | ja | oeffentlicher Quellenraum |
| `package_id` | nein | `source_id.effect_id` |
| `entry_file` | nein | `effect.py` |
| `entry_class` | nein | einzige lokale `BaseEffect`-Unterklasse |
| `min_service_version` | nein | `1.0.0` |
| `author` | nein | Paketmetadatum |
| `vendor` | nein | Paketmetadatum |

Titel, Beschreibung, Schemas und Typ stehen nicht doppelt im YAML-Manifest,
sondern in der `EffectDefinition` der Python-Klasse.

`effect.py` muss genau eine lokal definierte `BaseEffect`-Unterklasse
enthalten. Paketlokale Module und Assets werden mitgenommen. `common.py` und
`commands.json` sind in V2 nicht erlaubt.

## Anatomie eines LEFX-Pakets

Ein gebautes `.lefx` ist ein ZIP-Container:

```text
definition.lefx
|-- manifest.json
|-- effect-presets.json     optional
|-- payload/
|   |-- __init__.py
|   |-- effect.py
|   |-- assets/...
|   `-- extra/...
`-- hashes.json
```

`manifest.json` enthaelt:

- `format`, Paket-, Source-, Effekt- und qualifizierte ID,
- Titel, Beschreibung, Definitionstyp und Overlay-Modus,
- Definitionsversion und minimale Serviceversion,
- Runtime, Entry-Modul und Entry-Klasse,
- Defaults, Parameter- und Runtime-Input-Schema,
- visuellen Vertrag, Sampling, Layerregeln und Capabilities,
- optionale Tags, Autor, Vendor, Buildmetadaten,
  Hardwarekompatibilitaet und Lizenz.

Beim Laden muss das Manifest exakt zur geladenen Klassendefinition passen.
`hashes.json` verwendet SHA-256 und prueft die darin gelisteten
Paketbestandteile vor der Registrierung.

## ID-Arten

### Definition-ID

Die kurze Definition-ID ist die kanonische Benutzerform:

```text
rotating_segment
```

### Source-ID

Die Source-ID bezeichnet den Herausgeber- beziehungsweise Quellenraum:

```text
default-effects
```

### Package-ID

Die Package-ID identifiziert das konkrete Paket:

```text
default-effects.rotating_segment
```

### Qualifizierte ID

Die qualifizierte Form verbindet Quelle und lokale ID:

```text
default-effects::rotating_segment
```

Sie dient expliziter Quellenauswahl und Diagnosen. Im normalen Gebrauch bleibt
die kurze ID massgeblich.

## Globale Eindeutigkeit

Definition- und Preset-IDs teilen einen global eindeutigen oeffentlichen
Namensraum. Eine lokale ID darf deshalb nicht in zwei geladenen Quellen oder
zwischen Definition und Preset kollidieren.

Package-IDs und qualifizierte IDs bleiben exakte Aliase. Unscharfe Treffer
werden nur als Vorschlag gemeldet.

Overlay-Channels liegen in einem separaten Runtime-Namensraum.

### Aufloesungsformen

```text
Definition:
  effect_id
  source_id::effect_id
  package_id

Preset:
  preset_id
  source_id::preset_id
  source_id.preset_id
```

Kein Treffer liefert nach Moeglichkeit aehnliche ID-Vorschlaege. Mehr als ein
Treffer wird als Mehrdeutigkeit abgewiesen; es wird nichts automatisch
ausgefuehrt.

## Freie Konfiguration ist der Normalfall

Aufrufer duerfen jeden im Schema erlaubten Wert frei setzen:

```text
set state rotating_segment
  --config {"color":"gruen","speed":1.3,"segment_length":4}
```

Die Definition legt Typen und Grenzen fest, nicht eine kleine Liste
vorgefertigter Varianten.

## Presets als optionale Vorschlaege

Ein Preset ist ein benannter, kuratierter Ausgangspunkt:

```yaml
presets:
  rotating_segment_calm:
    title: Rotating Segment Calm
    params:
      color: "#4A7BFF"
      brightness: 0.45
      speed: 0.7
      segment_length: 4
```

Der Aufrufer kann das Preset unveraendert verwenden oder erlaubte Werte
ueberschreiben. Presets:

- sind optional,
- begrenzen die freie Konfiguration nicht,
- enthalten keine Runtime-Eingaben,
- veraendern keinen Typ, Layer oder Lebenszyklus,
- sind keine eigenen Definitionen.

Ein Preset besitzt:

- global eindeutige `preset_id`,
- `source_id` und referenzierte `effect_id`,
- `params`,
- optionale `title`, `description` und `tags`.

Alle Presetwerte werden beim Paket-Build gegen das Konfigurationsschema der
referenzierten Definition validiert.

## LEFXSET

Ein LEFXSET fasst mehrere vorgebaute LEFX-Pakete fuer Distribution und
Installation zusammen.

```text
rotating-segment.lefx
volume-ring.lefx
short-pulse.lefx
        \-> curated-effects.lefxset
```

Das Set fuegt kein Verhalten hinzu. Jedes Mitglied bleibt eine eigenstaendige
Definition mit eigener ID und eigenem Vertrag.

Thematische Sets duerfen den Produktkatalog uebersichtlich kuratieren, sind
aber keine fachlichen Typen. Die endgueltigen Namen des mitgelieferten
Katalogs werden bei dessen qualitativer Ueberarbeitung festgelegt.

### Source einer LEFXSET-Datei

```text
my_set/
|-- set.yaml
`-- effects/
    |-- rotating-segment.lefx
    |-- volume-ring.lefx
    `-- short-pulse.lefx
```

`set.json` ist alternativ moeglich. Das Setmanifest akzeptiert:

| Feld | Pflicht | Bedeutung |
|---|---:|---|
| `set_id` | ja | ID des Sets |
| `source_id` | ja | gemeinsamer Quellenraum |
| `title` | nein | Standard ist `set_id` |
| `version` | nein | Standard `1` |
| `min_service_version` | nein | Standard `1.0.0` |
| `effects` | nein | geordnete Mitgliederauswahl; sonst Verzeichnisinhalt |
| `description`, `tags` | nein | Katalogmetadaten |
| `author`, `vendor` | nein | Herausgebermetadaten |

Vorgebaute `.lefx` sind der bevorzugte Set-Input. Quellverzeichnisse werden
unterstuetzt, erzeugen aber eine Warnung. Alle Mitglieder muessen dieselbe
`source_id` wie das Set besitzen.

### Anatomie des gebauten Sets

```text
curated-effects.lefxset
|-- set-manifest.json
|-- effects/
|   |-- rotating-segment.lefx
|   |-- volume-ring.lefx
|   `-- short-pulse.lefx
`-- hashes.json
```

Presets bleiben Bestandteil des jeweiligen LEFX-Pakets. Das Set besitzt keine
eigene Preset- oder Commandlogik.

## Registry und Discovery

Die Standard-Registry sucht das First-Party-Set in dieser Reihenfolge:

1. Pfad aus `LED_CONTROLLER_DEFAULT_EFFECT_SET`,
2. `effects/default-effects.lefxset` neben Anwendung oder EXE,
3. passende Eintraege aus `build-tools/build_config.json`.

Weitere `.lefx` und `.lefxset` unter `packages/` werden automatisch gefunden.
Paketquellen koennen ausserdem im laufenden Service registriert, neu geladen
oder entfernt werden.

Ein Reload baut Registry, Presets und Aliase neu auf. Fehlerhafte Quellen
werden nicht teilweise eingetragen. Eine zur Laufzeit registrierte Quelle
wird derzeit nicht als dauerhafte Benutzerkonfiguration persistiert.

## Versionen

- LEFX-Paketformat: `lefx/2`
- LEFXSET-Format: `lefxset/2`
- `min_service_version`: minimale kompatible Serviceversion
- Definitions- und Paketversionen bleiben getrennte Angaben

V1-Pakete werden von V2 nicht still interpretiert oder automatisch
konvertiert.

`min_service_version` wird aktuell als Paketmetadatum transportiert. Eine
automatische Versionskompatibilitaetspruefung ist noch nicht implementiert.

## Integritaet und Vertrauen

SHA-256 erkennt veraenderte Paketdateien, beantwortet aber nicht, wer das
Paket erstellt hat. V2 besitzt derzeit:

- Hashpruefung,
- Manifest- und Klassengleichheitspruefung,
- Import-Whitelist beim Build eigener Quellen,
- keine digitale Signatur,
- keinen Trust Store,
- keine Python-Sandbox.

Ein LEFX-Paket enthaelt ausfuehrbaren Python-Code. Es darf deshalb nur aus
vertrauenswuerdiger Quelle geladen werden.
