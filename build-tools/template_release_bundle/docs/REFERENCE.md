# Referenz

## Service

- `serve`: lokalen Controller starten
- `ping`: Erreichbarkeit pruefen
- `status`: Laufzeitstatus lesen
- `reset`: Controller zuruecksetzen
- `shutdown`: Service beenden

## LEFX-V2-CLI

Discovery:

```text
list states|overlays|events|presets [--json] [--details]
show <id-or-preset>
```

Steuerung:

```text
set state <id-or-preset> [--slot background|primary] [--config JSON] [--on|--off|--toggle]
clear state [--slot background|primary]
set overlay <id-or-preset> [--channel NAME] [--config JSON] [--inputs JSON] [--on|--off|--toggle]
update overlay <channel> --inputs JSON
clear overlay <channel>
emit event <id-or-preset> [--config JSON] [--priority N]
```

Sichere Kurzformen:

```text
set <id-or-preset>
update <channel> --inputs JSON
clear <channel>
emit <id-or-preset>
```

Lokale IDs sind global eindeutig. Daher kann die CLI in den Kurzformen den
Typ sicher aufloesen. Ohne Aktionsflag bedeutet `set` immer `on`.
`/on`, `/off`, `/toggle`, `/json` und `/details` sind Windows-Aliase der
entsprechenden `--`-Flags.

## HTTP API V2

Discovery:

- `GET /api/v2/states`
- `GET /api/v2/overlays`
- `GET /api/v2/events`
- `GET /api/v2/presets`
- `GET /api/v2/show/{target}`

Operationen:

- `POST /api/v2/set/state`
- `POST /api/v2/clear/state`
- `POST /api/v2/set/overlay`
- `POST /api/v2/update/overlay`
- `POST /api/v2/clear/overlay`
- `POST /api/v2/emit/event`

Listen liefern standardmaessig Arrays lokaler IDs. `?details=true` fordert
den vollstaendigen Vertrag an. Die API verwendet kein implizites Toggle;
`action` ist `on`, `off` oder `toggle` und hat den Default `on`.

## Effekttypen

- State: unbestimmter Grundzustand auf `background` oder `primary`
- Overlay `controlled`: benannter Channel, per `update` veraenderbar
- Overlay `timed`: feste Dauer, beendet sich selbst
- Event: kurze endliche Anzeige mit Queue-Prioritaet

Layer sind intern und nicht frei waehlbar. Es gibt keinen oeffentlichen
`MAIN_LAYER`.

## Parameter

Definitionen trennen:

- `config`: stabile Konfiguration wie Farben oder Geschwindigkeit
- `inputs`: veraenderliche Laufzeitwerte kontrollierter Overlays

Werte werden strikt gegen Typ, Bereich und Enum validiert. Farben akzeptieren
kanonische Hexwerte sowie definierte deutsche und englische Farbnamen.

## Presets

Presets enthalten nur Konfigurationswerte. Sie duerfen Typ, Layer,
Lebenszyklus, Dauer, Queue-Verhalten oder Runtime-Eingaben nicht veraendern.
Eingebettete Effekt-Commands gehoeren nicht zum LEFX-V2-Vertrag.

## Effektquellen

Der Release-Build laedt die Standardbibliothek aus
`effects/default-effects.lefxset` neben der EXE. Weitere Quellen muessen als
`.lefx` oder `.lefxset` vorliegen.

Verwaltung:

- `list-effect-sources`
- `register-effect-source`
- `reload-effect-sources`
- `remove-effect-source`

## Kompatibilitaet

Status, Quellenverwaltung und einzelne anwendungsspezifische V1-Callbacks
bleiben vorlaeufig erhalten. Neue Effektintegrationen verwenden `/api/v2`.

## Wichtige Laufzeitdateien

- `effects/default-effects.lefxset`: Standardbibliothek
- `active_service.json`: PID, Host, Port und Status
- `background_state.json`: persistierter Background-State
- `logs/led_controller.log`: Basislogging
