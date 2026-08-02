# Zielarchitektur

Diese Datei beschreibt das Gesamtbild des Zielsystems nach der Neuausrichtung.

## Kernidee

Es gibt kuenftig genau **eine** offizielle Ausfuehrungs-Engine:

- der laufende Service
- mit einem Layer-System als Source of Truth
- mit einer vorgeschalteten Normalisierungsschicht
- und ohne direkte Umgehung der Engine fuer CLI, API, Adapter oder Komfort-Frontends

## Systemuebersicht

```mermaid
flowchart LR
    A["CLI"] --> N["Normalisierung"]
    B["REST API"] --> N
    C["Adapter / Wrapper"] --> N
    D["Komfort-API"] --> N
    E["Preset / App Mapping"] --> N
    N --> G["Engine Commands"]
    G --> L["Layer Store"]
    L --> C2["Composer"]
    C2 --> R["Renderer"]
    R --> O["Frame Output"]
    O --> H["Hardware / Preview Adapter"]
```

## Schichten des Zielsystems

```mermaid
flowchart TD
    U["Eingabequellen"] --> N["Normalisierte Kommandos"]
    N --> I["Effect Invocation"]
    I --> LS["Layer State"]
    LS --> SC["Scene Composition"]
    SC --> FR["Final Frame"]
    FR --> AD["Adapter"]
```

## Finale Layer

```mermaid
flowchart BT
    B["BACKGROUND_STATE_LAYER (100)"]
    S["STATE_LAYER (200)"]
    M["MAIN_LAYER (300)"]
    T["TEMP_OVERLAY_LAYER (400)"]
    O["ONGOING_OVERLAY_LAYER (500)"]
    E["EVENT_LAYER (600)"]
```

## Layer-Semantik

| Layer | Prioritaet | Zweck | Typisches Verhalten |
|---|---:|---|---|
| `BACKGROUND_STATE_LAYER` | 100 | unterste persistente Grundanzeige | dauerhaft, restorable |
| `STATE_LAYER` | 200 | laufender Anwendungszustand | dauerhaft, nicht persistent |
| `MAIN_LAYER` | 300 | freie Hauptanzeige | endlich oder unendlich |
| `TEMP_OVERLAY_LAYER` | 400 | zeitlich begrenzte Einblendung | endlich |
| `ONGOING_OVERLAY_LAYER` | 500 | unbegrenzte, temporaere Ueberlagerung | unbestimmt |
| `EVENT_LAYER` | 600 | kurze Ereigniseffekte | Queue, Priorisierung |

## Datenfluss einer Set-Operation

```mermaid
sequenceDiagram
    participant X as "Aufrufer"
    participant N as "Normalisierung"
    participant V as "Validierung"
    participant E as "Engine"
    participant L as "Layer"
    participant C as "Composer"
    participant R as "Renderer"

    X->>N: "set effect / fachlicher Befehl"
    N->>V: "NormalizedCommand"
    V->>E: "EffectInvocation"
    E->>L: "ersetzen / queue / enabled"
    E->>C: "aktuelle Layer"
    C->>R: "Scene"
    R-->>X: "sichtbare Ausgabe"
```

## Was die Engine kuenftig nicht mehr direkt wissen soll

- keine fachlichen Namen wie `listening`, `warning`, `recording`
- keine App-spezifischen Sonderpfade
- keine separaten Spezialbehandlungen fuer `direction`, `countdown`, `progress`

Diese Dinge sollen vor der Engine in normale Effekt-Invocations uebersetzt werden.

## Was die Engine kuenftig wissen soll

- welche Layer es gibt
- welche Prioritaeten sie haben
- welche Effektdefinitionen registriert sind
- welche Effektinstanzen gerade aktiv sind
- welche Validierungs- und Queue-Regeln gelten
- wie daraus die finale Scene zusammengesetzt wird
