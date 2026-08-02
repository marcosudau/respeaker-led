# HTTP-API-Referenz

Diese Seite dokumentiert die HTTP-Schnittstelle des laufenden
LED-Controller-Service. Fuer die Kommandozeile gilt die getrennte
[CLI-Referenz](cli_guide.md).

## Basisdaten

| Eigenschaft | Wert |
|---|---|
| Standardadresse | `http://127.0.0.1:8765` |
| Ziel-API | `/api/v2` |
| Transportformat | JSON |
| Content-Type bei Requests | `application/json` |
| Interaktive OpenAPI-Oberflaeche | `/docs` |
| OpenAPI-Dokument | `/openapi.json` |

Der effektiv verwendete Port kann vom angeforderten Port abweichen, wenn der
Service mit einem Portpool gestartet wurde. Host-Anwendungen koennen Host und
Port aus `active_service.json` lesen.

## Endpunktuebersicht

### Allgemein

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/` | Service-Metadaten und Einstiegspfade |
| `GET` | `/health` | knapper Betriebszustand |
| `GET` | `/docs` | interaktive FastAPI-Dokumentation |
| `GET` | `/openapi.json` | maschinenlesbares OpenAPI-Schema |

### V2: Discovery und Metadaten

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/api/v2/states` | State-IDs oder State-Details |
| `GET` | `/api/v2/overlays` | Overlay-IDs oder Overlay-Details |
| `GET` | `/api/v2/events` | Event-IDs oder Event-Details |
| `GET` | `/api/v2/presets` | Preset-IDs oder Preset-Details |
| `GET` | `/api/v2/show/{target:path}` | ein Ziel vollstaendig aufloesen |

### V2: Steuerung

| Methode | Pfad | Zweck |
|---|---|---|
| `POST` | `/api/v2/set/state` | State setzen, deaktivieren oder umschalten |
| `POST` | `/api/v2/clear/state` | State-Slot leeren |
| `POST` | `/api/v2/set/overlay` | Controlled oder Timed Overlay setzen |
| `POST` | `/api/v2/update/overlay` | Runtime-Eingaben eines Channels aktualisieren |
| `POST` | `/api/v2/clear/overlay` | Overlay-Channel entfernen |
| `POST` | `/api/v2/emit/event` | Event in die Queue einreihen |

### V1: Betrieb und Quellenverwaltung

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/api/v1/ping` | Verbindung und Renderloop pruefen |
| `GET` | `/api/v1/status` | vollstaendigen Runtime-Snapshot lesen |
| `GET` | `/api/v1/effects` | registrierte Definitionen mit Details |
| `GET` | `/api/v1/effects/{source_id}` | Definitionen einer Quelle |
| `GET` | `/api/v1/effects/{source_id}/{effect_id}` | Definition einer Quelle |
| `GET` | `/api/v1/effects/{source_id}/{effect_id}/presets` | Presets einer Definition |
| `GET` | `/api/v1/effect-presets/{source_id}/{preset_id}` | ein Preset |
| `GET` | `/api/v1/effect-sources` | Paketquellen auflisten |
| `POST` | `/api/v1/effect-sources/register` | `.lefx` oder `.lefxset` registrieren |
| `POST` | `/api/v1/effect-sources/reload` | Registry neu aufbauen |
| `DELETE` | `/api/v1/effect-sources/{source_id}` | Quelle entfernen |

### V1: Anwendungskompatibilitaet

| Methode | Pfad |
|---|---|
| `POST` | `/api/v1/commands/set_state` |
| `POST` | `/api/v1/commands/clear_state` |
| `POST` | `/api/v1/commands/emit_event` |
| `POST` | `/api/v1/commands/reset` |
| `POST` | `/api/v1/commands/shutdown` |
| `POST` | `/api/v1/commands/start_timeout_countdown` |
| `POST` | `/api/v1/commands/update_timeout_countdown` |
| `POST` | `/api/v1/commands/cancel_timeout_countdown` |
| `POST` | `/api/v1/commands/set_direction` |
| `POST` | `/api/v1/commands/clear_direction` |
| `POST` | `/api/v1/commands/set_brightness` |
| `POST` | `/api/v1/commands/set_enabled` |

Neue Integrationen verwenden fuer States, Overlays und Events die V2-Routen.
Die V1-Anwendungskommandos bleiben vorlaeufig fuer bestehende Aufrufer.

## Allgemeine Endpunkte

### `GET /`

Liefert Servicekennung, Version, Dokumentationspfade, V2-Basis,
Ausgabemodus und die Verben `list`, `show`, `set`, `clear`, `update`, `emit`.

### `GET /health`

Antwortfelder:

| Feld | Bedeutung |
|---|---|
| `status` | `ok` oder `degraded` |
| `render_loop_running` | Renderthread laeuft |
| `render_count` | bisher erzeugte Frames |
| `last_error` | letzter Renderfehler oder `null` |
| `output_mode` | zum Beispiel `device` oder `console-preview` |
| `fallback_active` | Hardware-Fallback ist aktiv |
| `hardware_inputs` | Status zentral gepollter Hardwareprovider, beispielsweise `respeaker_doa` |

`degraded` bedeutet, dass ein Fehler oder Hardware-Fallback vorliegt. Der
HTTP-Endpunkt kann dabei weiterhin erfolgreich mit Status 200 antworten.

## V2-Discovery

### Listen

```http
GET /api/v2/states
GET /api/v2/overlays
GET /api/v2/events
GET /api/v2/presets
```

Ohne Queryparameter kommt eine kompakte Liste lokaler IDs:

```json
["fill_ring", "rotating_segment", "yin_yang_spin"]
```

Mit `details=true` kommen vollstaendige Eintraege:

```http
GET /api/v2/overlays?details=true
```

Nur Presets unterstuetzen zusaetzlich einen Typfilter:

```http
GET /api/v2/presets?type=state
GET /api/v2/presets?type=overlay
GET /api/v2/presets?type=event
```

`type` darf nur `state`, `overlay` oder `event` sein.

### Definition-Detailobjekt

Ein V2-Detailobjekt enthaelt:

| Feld | Bedeutung |
|---|---|
| `id` | lokale Definition-ID |
| `qualified_id` | `source_id::id` |
| `source_id` | Paketquelle |
| `package_id` | konkretes LEFX-Paket |
| `type` | `state`, `overlay` oder `event` |
| `overlay_mode` | `controlled`, `timed` oder `null` |
| `title`, `description` | lesbare Metadaten |
| `version` | Definitionsversion |
| `defaults` | Standardkonfiguration |
| `parameters` | Konfigurationsschema |
| `runtime_inputs` | Runtime-Input-Schema |
| `visual` | Farbmodell, Komposition, Animation, Richtung |
| `input_sampling` | Push-/Pull- und Heartbeat-Policy oder `null` |
| `tags` | Katalogbegriffe |

Jeder Parameter unter `parameters` oder `runtime_inputs` kann diese Felder
tragen:

```json
{
  "type": "float",
  "required": false,
  "default": 1.0,
  "description": "Helligkeitsfaktor.",
  "minimum": 0.0,
  "maximum": 1.0,
  "enum_values": [],
  "unit": "ratio",
  "nullable": false,
  "aliases": []
}
```

### `GET /api/v2/show/{target:path}`

`target` darf sein:

- lokale Definition-ID,
- lokale Preset-ID,
- qualifizierte Definition-ID,
- qualifizierte Preset-ID,
- Package-ID einer Definition.

Die Antwort entspricht dem Definition-Detailobjekt und ergaenzt:

| Feld | Bedeutung |
|---|---|
| `resolved_from` | urspruengliche Eingabe |
| `resolved_kind` | `definition` oder `preset` |
| `preset` | bei Preset: qualifizierte ID und Konfiguration |

Unbekannte Ziele liefern 404. Mehrdeutige Ziele liefern 409.

## Gemeinsame V2-Felder

### `target`

Definition oder Preset. Der Endpunkt prueft den erwarteten Typ. Ein
Event-Preset kann beispielsweise nicht ueber `/set/state` aktiviert werden.

### `config`

Stabile Konfiguration der Instanz. Aufloesungsreihenfolge:

```text
Definition-Defaults -> Preset -> config
```

Unterstuetzte Eingabeformen und Farbaliasse stehen unter
[Parameter und Werte](effect-system/06_parameters_and_values.md).

### `inputs`

Mutable Runtime-Eingaben eines Controlled Overlays. Timed Overlays, States
und Events akzeptieren keine Runtime-Eingaben.

### `action`

| Wert | Verhalten |
|---|---|
| `on` | Ziel sicher aktivieren; Standard |
| `off` | nur dieses aktive Ziel entfernen |
| `toggle` | Zustand dieses Ziels umschalten |

Timed Overlays akzeptieren nur `on`. Events besitzen kein `action`.

## `POST /api/v2/set/state`

Request:

```json
{
  "target": "soft_pulse",
  "config": {
    "color": "blau",
    "speed": 0.8
  },
  "slot": "primary",
  "action": "on"
}
```

| Feld | Typ | Pflicht | Standard | Erlaubt |
|---|---|---:|---|---|
| `target` | String | ja | - | State-ID oder State-Preset |
| `config` | Objekt | nein | `{}` | laut Definition |
| `slot` | String | nein | `primary` | `background`, `primary` |
| `action` | String | nein | `on` | `on`, `off`, `toggle` |

`off` und `toggle` entfernen keinen anderen State, der inzwischen denselben
Slot belegt.

## `POST /api/v2/clear/state`

```json
{"slot": "primary"}
```

| Feld | Typ | Pflicht | Standard | Erlaubt |
|---|---|---:|---|---|
| `slot` | String | nein | `primary` | `background`, `primary` |

Der Slot wird unabhaengig von seiner aktuellen Definition geleert.

## `POST /api/v2/set/overlay`

Controlled Overlay:

```json
{
  "target": "direction_indicator",
  "channel": "doa",
  "config": {
    "color": "gruen"
  },
  "inputs": {
    "direction_deg": 120
  },
  "action": "on"
}
```

Timed Overlay:

```json
{
  "target": "countdown_ring",
  "config": {
    "total_ms": "5s"
  }
}
```

| Feld | Typ | Pflicht | Standard | Bedeutung |
|---|---|---:|---|---|
| `target` | String | ja | - | Overlay-ID oder Overlay-Preset |
| `channel` | String oder `null` | bedingt | `null` | Pflicht bei Controlled Overlay |
| `config` | Objekt | nein | `{}` | stabile Konfiguration |
| `inputs` | Objekt | nein | `{}` | nur Controlled Overlay |
| `action` | String | nein | `on` | bei Controlled: `on`, `off`, `toggle` |

Channels werden getrimmt, kleingeschrieben und mit `_` statt `-`
gespeichert. Ein leerer Channel ist ungueltig.

## `POST /api/v2/update/overlay`

```json
{
  "channel": "doa",
  "inputs": {
    "direction_deg": 240
  }
}
```

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---:|---|
| `channel` | String | ja | aktiver Controlled-Overlay-Channel |
| `inputs` | Objekt | nein | zu aktualisierende deklarierte Felder |

Ein leeres `inputs`-Objekt ist ein gueltiges Lebenszeichen. Es behaelt die
letzten Werte und aktualisiert den erfolgreichen Empfangszeitpunkt.

Unbekannter Channel: 404. Timed Overlay oder ungueltige Inputs: 422.

## `POST /api/v2/clear/overlay`

```json
{"channel": "doa"}
```

Entfernt die aktive Instanz dieses Channels. Ein unbekannter Channel liefert
404.

## `POST /api/v2/emit/event`

```json
{
  "target": "warning_flash",
  "config": {
    "color": "rot",
    "duration_ms": 900
  },
  "priority": 610
}
```

| Feld | Typ | Pflicht | Standard | Bedeutung |
|---|---|---:|---|---|
| `target` | String | ja | - | Event-ID oder Event-Preset |
| `config` | Objekt | nein | `{}` | Event-Konfiguration |
| `priority` | Integer oder `null` | nein | Layerstandard | Queue-Sortierung |

Hoehere Prioritaet wird vor niedrigeren wartenden Events abgespielt. Bei
Gleichheit gilt FIFO. Das bereits aktive Event wird nicht unterbrochen.

## V2-Erfolgsantworten

Mutierende V2-Endpunkte liefern ein Objekt mit:

```json
{
  "ok": true,
  "operation": "set",
  "type": "state",
  "target": "soft_pulse",
  "slot": "primary",
  "action": "on",
  "status": {}
}
```

Je nach Operation sind `target`, `slot`, `channel` oder `action` vorhanden.
`status` ist der unmittelbar nach der Mutation gerenderte Runtime-Snapshot.

## Fehlerformat

### Parameter- und Inputvalidierung

HTTP 422:

```json
{
  "detail": {
    "code": "validation_failed",
    "issues": [
      {
        "code": "unknown_field",
        "field": "config.colour",
        "message": "Unknown field 'colour'",
        "value": "blue",
        "suggestions": ["color"]
      }
    ]
  }
}
```

Moegliche Issue-Codes umfassen unter anderem:

- `unknown_field`
- `conflicting_fields`
- `missing_required`
- `invalid_value`
- `unknown_color`
- `color_out_of_range`
- `invalid_duration`
- `duration_out_of_range`
- `invalid_ratio`
- `ratio_out_of_range`
- `invalid_angle`
- `invalid_boolean`

### Weitere Statuscodes

| Status | Bedeutung |
|---:|---|
| 200 | Operation oder Abfrage erfolgreich |
| 404 | Ziel oder Channel unbekannt |
| 409 | Zielreferenz mehrdeutig |
| 422 | Requestschema, Typvertrag oder Wert ungueltig |
| 500 | unerwarteter interner Fehler |

Ein abgewiesenes V2-Steuerungskommando veraendert den Runtime-Zustand nicht.

## `GET /api/v1/ping`

Antwort:

```json
{
  "ok": true,
  "render_loop_running": true,
  "output_mode": "device",
  "timestamp": 1785420000.0
}
```

## `GET /api/v1/status`

Der Status enthaelt:

- `base_state`: anwendungsspezifischer Kompatibilitaetszustand,
- `direction`, `countdown`, `brightness`, `enabled`,
- `event_overlay.current` und `event_overlay.pending`,
- `render_layers` fuer Background, Primary, Controlled und Timed Overlay,
- `last_scene` und `last_frame`,
- Servicefelder wie FPS, Renderanzahl, Fehler und Hardware-Fallback.

Aktive Controlled Overlays enthalten `input_health` mit:

```json
{
  "mode": "push",
  "status": "healthy",
  "age_ms": 120,
  "missed_heartbeats": 0,
  "max_missed_heartbeats": 3,
  "last_error": null
}
```

## V1-Quellenverwaltung

### Quelle registrieren

```http
POST /api/v1/effect-sources/register
```

```json
{
  "path": "C:\\effects\\my-effects.lefxset",
  "enabled": true
}
```

`path` muss fuer den Serviceprozess erreichbar sein und auf `.lefx` oder
`.lefxset` zeigen. Paket, Hashes, Source-ID und globale Ziel-IDs werden vor der
Registrierung validiert.

### Quellen neu laden

```http
POST /api/v1/effect-sources/reload
```

Kein Requestbody erforderlich. Konfigurierte und automatisch gefundene
Quellen werden neu eingelesen.

### Quelle entfernen

```http
DELETE /api/v1/effect-sources/{source_id}
```

Entfernt die Quelle aus der laufenden Registry. Das Paket auf dem Dateisystem
wird nicht geloescht.

## V1-Anwendungskommandos

Diese Routen bilden alte fachliche Controller-Aufrufe auf die V2-Runtime ab.
Sie sind keine Vorlage fuer neue generische Integrationen.

| Pfad | JSON-Body |
|---|---|
| `/commands/set_state` | `{"state_name":"recording","payload":{}}` |
| `/commands/clear_state` | `{"state_name":null}` |
| `/commands/emit_event` | `{"event_name":"warning","payload":{}}` |
| `/commands/start_timeout_countdown` | `{"total_ms":5000,"remaining_ms":5000,"follow_up_state":"idle","payload":{}}` |
| `/commands/update_timeout_countdown` | `{"remaining_ms":2500}` |
| `/commands/set_direction` | `{"direction":120}` |
| `/commands/set_brightness` | `{"level":0.7}` |
| `/commands/set_enabled` | `{"enabled":true}` |

Diese Routen erwarten keinen Body:

- `/commands/reset`
- `/commands/shutdown`
- `/commands/cancel_timeout_countdown`
- `/commands/clear_direction`

## Curl-Beispiele

```powershell
curl.exe http://127.0.0.1:8765/api/v2/states
```

```powershell
curl.exe -X POST http://127.0.0.1:8765/api/v2/set/state `
  -H "Content-Type: application/json" `
  -d '{"target":"soft_pulse","slot":"primary","action":"on","config":{"color":"blau"}}'
```

```powershell
curl.exe -X POST http://127.0.0.1:8765/api/v2/update/overlay `
  -H "Content-Type: application/json" `
  -d '{"channel":"doa","inputs":{"direction_deg":240}}'
```

## Weiterfuehrend

- [CLI-Referenz](cli_guide.md)
- [Bedienmodell und Semantik](effect-system/09_control_interface.md)
- [Parameter und Eingabeformen](effect-system/06_parameters_and_values.md)
- [Runtime-Eingaben](effect-system/07_runtime_inputs.md)
- [Aktuelle Architektur](dev/architecture.md)
