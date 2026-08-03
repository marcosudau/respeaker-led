# CLI-Referenz

Diese Seite dokumentiert die vollstaendige Kommandozeilenschnittstelle von
`main.py`. Fuer direkte HTTP-Aufrufe gilt die getrennte
[HTTP-API-Referenz](api_guide.md).

## Aufruf

```powershell
python .\main.py [globale Optionen] <Kommando> [Kommandooptionen]
```

Hilfe:

```powershell
python .\main.py --help
python .\main.py <Kommando> --help
```

## Kommandoueberblick

### V2-Zieloberflaeche

| Kommando | Zweck |
|---|---|
| `list` | States, Overlays, Events oder Presets auflisten |
| `show` | ein Ziel und seinen Vertrag anzeigen |
| `set` | State oder Overlay setzen |
| `clear` | State-Slot oder Overlay-Channel leeren |
| `update` | Controlled Overlay aktualisieren |
| `emit` | Event ausloesen |

### Service und Paketquellen

| Kommando | Zweck |
|---|---|
| `serve` | Controller-Service starten |
| `ping` | Erreichbarkeit pruefen |
| `status` | Runtime- und Servicezustand lesen |
| `shutdown` | laufenden Service beenden |
| `list-effect-sources` | Paketquellen auflisten |
| `register-effect-source` | `.lefx` oder `.lefxset` registrieren |
| `reload-effect-sources` | Paketquellen neu laden |
| `remove-effect-source` | Quelle aus der Registry entfernen |

### Anwendungskompatibilitaet

| Kommando | Zweck |
|---|---|
| `set-state`, `clear-state` | alte fachliche State-Schnittstelle |
| `emit-event` | altes fachliches Event |
| `reset` | alten Controllerzustand zuruecksetzen |
| `start-countdown` | anwendungsspezifischen Countdown starten |
| `update-countdown` | Countdown aktualisieren |
| `cancel-countdown` | Countdown abbrechen |
| `set-direction`, `clear-direction` | Richtungsanzeige steuern |
| `set-brightness` | globale Ausgabehelligkeit setzen |
| `set-enabled` | LED-Ausgabe aktivieren oder deaktivieren |

Neue Integrationen verwenden `list`, `show`, `set`, `clear`, `update` und
`emit`. Die Kompatibilitaetskommandos bleiben fuer vorhandene Anwendungen.

## Globale Optionen

Globale Optionen stehen vor dem Kommando:

| Option | Typ | Standard | Bedeutung |
|---|---|---:|---|
| `--no-device` | Schalter | aus | bei `serve` Konsolenvorschau statt ReSpeaker |
| `--fps` | Float | `8.0` | Renderframes pro Sekunde |

Beispiel:

```powershell
python .\main.py --no-device --fps 12 serve
```

`--fps` ist die Engine-Framerate. Der Parameter `speed` einer Definition ist
dagegen ein Multiplikator der paketlokalen Animation.

## Verbindungsoptionen

Alle Kommandos, die einen laufenden Service ansprechen, akzeptieren:

| Option | Typ | Standard | Bedeutung |
|---|---|---:|---|
| `--host` | String | `127.0.0.1` | Servicehost |
| `--port` | Integer | `8765` | Serviceport |
| `--timeout` | Float | `2.0` | HTTP-Timeout in Sekunden |

Sie stehen nach dem Kommando:

```powershell
python .\main.py status --host 127.0.0.1 --port 8766 --timeout 5
```

## JSON-Argumente in PowerShell

`--config`, `--inputs` und `--payload` erwarten jeweils ein JSON-Objekt:

```powershell
--config '{"color":"blau","brightness":0.8}'
```

Arrays oder Einzelwerte sind nicht erlaubt:

```text
ungueltig: --config '["blue"]'
ungueltig: --config '"blue"'
```

In PowerShell schuetzen einfache Anfuehrungszeichen die doppelten
JSON-Anfuehrungszeichen.

## `list`

Syntax:

```powershell
python .\main.py list <kind> [--details] [--json]
```

`kind` akzeptiert Singular und Plural:

```text
state, states
overlay, overlays
event, events
preset, presets
```

Ausgabeformen:

| Aufruf | Ausgabe |
|---|---|
| `list states` | eine lokale ID pro Zeile |
| `list states --json` | JSON-Array lokaler IDs |
| `list states --details` | JSON-Array vollstaendiger Vertraege |

Beispiele:

```powershell
python .\main.py list states
python .\main.py list overlays --json
python .\main.py list events --details
python .\main.py list presets --details
```

## `show`

Syntax:

```powershell
python .\main.py show <target> [--json]
```

`target` kann eine Definition, ein Preset, eine qualifizierte ID oder eine
Package-ID sein.

```powershell
python .\main.py show rotating_segment
python .\main.py show default-effects::rotating_segment
python .\main.py show rotating_segment_calm
```

Die Ausgabe ist immer das vollstaendige JSON-Detailobjekt. `--json` wird als
explizite Schreibweise akzeptiert, veraendert diese ohnehin
maschinenlesbare Ausgabe aber nicht.

## `set state`

Syntax:

```powershell
python .\main.py set state <target> `
  [--slot background|primary] `
  [--config <JSON-Objekt>] `
  [--on|--off|--toggle]
```

| Eingabe | Standard | Bedeutung |
|---|---|---|
| `<target>` | Pflicht | State-Definition oder State-Preset |
| `--slot` | `primary` | `background` oder `primary` |
| `--config` | `{}` | explizite Konfigurationswerte |
| kein Modus / `--on` | `on` | sicher aktivieren |
| `--off` | - | dieses Ziel sicher deaktivieren |
| `--toggle` | - | dieses Ziel umschalten |

Beispiele:

```powershell
python .\main.py set state soft_pulse
python .\main.py set state solid_color --slot background `
  --config '{"color":"#224466","brightness":0.4}'
python .\main.py set state soft_pulse --off
python .\main.py set state soft_pulse --toggle
```

`off` und `toggle` wirken nur, wenn genau dieses Ziel im angegebenen Slot
aktiv ist.

## `clear state`

Syntax:

```powershell
python .\main.py clear state [--slot background|primary]
```

Ohne `--slot` wird `primary` geleert:

```powershell
python .\main.py clear state
python .\main.py clear state --slot background
```

## `set overlay`

Syntax:

```powershell
python .\main.py set overlay <target> `
  [--channel <name>] `
  [--config <JSON-Objekt>] `
  [--inputs <JSON-Objekt>] `
  [--on|--off|--toggle]
```

| Eingabe | Controlled Overlay | Timed Overlay |
|---|---|---|
| `<target>` | Pflicht | Pflicht |
| `--channel` | Pflicht | nicht erforderlich |
| `--config` | optional | optional |
| `--inputs` | optional | muss leer bleiben |
| `--on` | erlaubt | erlaubt |
| `--off`, `--toggle` | erlaubt | nicht erlaubt |

Controlled Overlay:

```powershell
python .\main.py set overlay direction_indicator `
  --channel doa `
  --config '{"color":"gruen"}' `
  --inputs '{"direction_deg":120}'
```

Timed Overlay:

```powershell
python .\main.py set overlay countdown_circle `
  --config '{"total_ms":"5s"}'
```

Channels werden normalisiert: Leerzeichen am Rand entfallen,
Grossbuchstaben werden klein und `-` wird `_`.

## `update overlay`

Syntax:

```powershell
python .\main.py update overlay <channel> --inputs <JSON-Objekt>
```

Beispiele:

```powershell
python .\main.py update overlay doa --inputs '{"direction_deg":240}'
python .\main.py update overlay doa --inputs '{}'
```

Ein leeres Objekt ist ein Lebenszeichen und behaelt die letzten gueltigen
Werte. Nur deklarierte Runtime-Felder sind erlaubt.

## `clear overlay`

Syntax:

```powershell
python .\main.py clear overlay <channel>
```

```powershell
python .\main.py clear overlay doa
```

## `emit event`

Syntax:

```powershell
python .\main.py emit event <target> `
  [--config <JSON-Objekt>] `
  [--priority <Integer>]
```

Beispiele:

```powershell
python .\main.py emit event warning_flash
python .\main.py emit event warning_flash `
  --config '{"color":"rot","duration_ms":900}' `
  --priority 610
```

Events besitzen keinen Aktivierungsmodus und keinen Channel. Sie werden nach
Prioritaet und bei Gleichheit FIFO eingereiht.

## Eindeutige Kurzformen

Die CLI kann den Typ einer global eindeutigen Ziel-ID ueber `show` aufloesen:

```powershell
python .\main.py set soft_pulse
python .\main.py set direction_indicator --channel doa `
  --inputs '{"direction_deg":120}'
python .\main.py emit warning_flash
python .\main.py update doa --inputs '{"direction_deg":240}'
python .\main.py clear doa
```

Diese Formen werden akzeptiert, die expliziten Langformen bleiben die
kanonische Dokumentationsform.

## Windows-Schalter

Neben den normalen Schaltern werden diese Slash-Aliase akzeptiert:

| Normal | Windows-Alias |
|---|---|
| `--on` | `/on` |
| `--off` | `/off` |
| `--toggle` | `/toggle` |
| `--json` | `/json` |
| `--details` | `/details` |

## `serve`

Syntax:

```powershell
python .\main.py [--no-device] [--fps <Float>] serve `
  [--host <Host>] `
  [--port <Port>] `
  [--port-pool <Liste>]
```

| Option | Standard | Bedeutung |
|---|---|---|
| `--host` | `127.0.0.1` | Bind-Adresse |
| `--port` | `8765` | bevorzugter Port |
| `--port-pool` | Standardpool | kommaseparierte Ports oder Bereiche |

Portpool-Beispiele:

```powershell
--port-pool 8765,8766,8767
--port-pool 8765-8770
--port-pool 8765,8770-8774
```

Der angeforderte Port wird zuerst geprueft. Danach wird der erste freie Port
aus dem Pool verwendet. Beim Start schreibt der Prozess ein JSON-Objekt mit
PID, Host, effektivem Port, angefordertem Port, Status und Logdatei auf
stdout.

Existiert laut `active_service.json` bereits eine Instanz, versucht der neue
Prozess sie geordnet zu beenden und uebernimmt danach.

## `ping`, `status` und `shutdown`

```powershell
python .\main.py ping
python .\main.py status
python .\main.py shutdown
```

- `ping` liefert einen kleinen Verbindungs- und Renderloop-Status.
- `status` liefert den vollstaendigen Runtime-Snapshot.
- `shutdown` setzt zunaechst den Kompatibilitaetszustand
  `service_stopping` und beendet dann den Service.

## Paketquellen

### Auflisten

```powershell
python .\main.py list-effect-sources
```

Die JSON-Ausgabe enthaelt je Quelle:

- `source_id`
- `path`
- `kind`
- `enabled`
- `autodiscovered`
- `package_id`
- `package_version`
- `preset_count`

### Registrieren

```powershell
python .\main.py register-effect-source <path> [--enabled <bool>]
```

```powershell
python .\main.py register-effect-source C:\effects\my-effects.lefxset
python .\main.py register-effect-source C:\effects\single.lefx --enabled false
```

`--enabled` akzeptiert:

```text
wahr:   1, true, yes, on
falsch: 0, false, no, off
```

Der Pfad muss fuer den Serviceprozess erreichbar sein.

### Neu laden

```powershell
python .\main.py reload-effect-sources
```

Alle konfigurierten und automatisch gefundenen Paketquellen werden erneut
validiert und registriert.

### Entfernen

```powershell
python .\main.py remove-effect-source <source_id>
```

Das Kommando entfernt die Source aus der laufenden Registry. Die Paketdatei
wird nicht geloescht.

## Kompatibilitaetskommandos

### State

```powershell
python .\main.py set-state <state_name> [--payload <JSON-Objekt>]
python .\main.py clear-state [state_name]
python .\main.py reset
```

### Event

```powershell
python .\main.py emit-event <event_name> `
  [--payload <JSON-Objekt>] `
  [--duration-ms <Integer>] `
  [--priority <Integer>] `
  [--source <String>] `
  [--reason <String>]
```

Explizite Optionen ergaenzen beziehungsweise ueberschreiben die
gleichnamigen Eintraege im Payload.

### Countdown

```powershell
python .\main.py start-countdown <total_ms> `
  [--remaining-ms <Integer>] `
  [--follow-up-state <Name>] `
  [--payload <JSON-Objekt>]

python .\main.py update-countdown <remaining_ms>
python .\main.py cancel-countdown
```

### Richtung

```powershell
python .\main.py set-direction <Float>
python .\main.py clear-direction
```

### Globale Ausgabe

```powershell
python .\main.py set-brightness <Float>
python .\main.py set-enabled <bool>
```

`set-brightness` begrenzt Werte auf den Bereich `0.0` bis `1.0`.
`set-enabled` akzeptiert dieselben englischen Boolean-Werte wie
`register-effect-source --enabled`.

## Ausgabe und Exitcodes

- Standardlisten: eine ID pro Zeile.
- Listen mit `--json` oder `--details`: eingeruecktes JSON.
- `show`, Mutationen, Quellenverwaltung und Status: eingeruecktes JSON.
- Erfolg: Exitcode `0`.
- fachlich fehlgeschlagenes Clientresultat: Exitcode `1`.
- fehlerhafte Kommandozeilensyntax: Exitcode `2`.
- Transport-, JSON- und Startfehler beenden den Prozess ebenfalls ungleich
  null und liefern eine Fehlermeldung.

## Weiterfuehrend

- [HTTP-API-Referenz](api_guide.md)
- [Schnellstart](getting_started.md)
- [Bedienmodell und Semantik](effect-system/09_control_interface.md)
- [Parameter und Eingabeformen](effect-system/06_parameters_and_values.md)
- [Troubleshooting](troubleshooting.md)
