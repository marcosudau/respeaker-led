# Public Entry Points

Stand: LEFX V2, 2026-07-29.

## Baseline

```powershell
pytest -q
python .\tools\effect_building\build_lefxset.py --rebuild-packages
```

## Runtime Controller

Die typisierten Kernoperationen von
`src.engine.runtime.ControllerRuntime` sind:

- `set_state_target(target, config, slot="primary", action="on")`
- `clear_state_target(slot="primary")`
- `set_overlay(target, channel, config, inputs, action="on")`
- `update_overlay(channel, inputs)`
- `clear_overlay(channel)`
- `emit_event_target(target, config, priority=None)`
- `render_once(now=None)`
- `get_status(now=None)`

Direkte Layer-Manipulation ist kein oeffentlicher V2-Vertrag.
Anwendungsspezifische Legacy-Callbacks werden separat ueber
`src/integrations/application_commands.py` uebersetzt.

## Service Wrapper

Die V2-Methoden von `src.services.service.ControllerService` sind:

- `list_definitions(definition_type, details=False)`
- `list_presets_v2(definition_type=None, details=False)`
- `target_info(target)`
- `set_state_target(...)`
- `clear_state_target(...)`
- `set_overlay_target(...)`
- `update_overlay_target(...)`
- `clear_overlay_target(...)`
- `emit_event_target(...)`

Betrieb und Quellenverwaltung:

- `start()`, `stop()`, `snapshot()`, `ping()`, `get_status()`
- `list_effect_sources()`
- `register_effect_source(path, enabled=True)`
- `reload_effect_sources()`
- `remove_effect_source(source_id)`

## Local Client

`src.interfaces.client.LocalControllerClient` spiegelt die HTTP-V2-Routen:

- `list_v2(kind, details=False)`
- `show_target(target)`
- `set_state_target(...)`
- `clear_state_target(...)`
- `set_overlay_target(...)`
- `update_overlay_target(...)`
- `clear_overlay_target(...)`
- `emit_event_target(...)`

Der Client ist standardmaessig Best-Effort. Mit `best_effort=False` werden
Transport- und API-Fehler als Exceptions weitergegeben.

## CLI

Oeffentliche V2-Kommandos:

- `list state|overlay|event|preset`
- `show <target>`
- `set state|overlay ...`
- `clear state|overlay ...`
- `update overlay ...`
- `emit event ...`

Sichere Kurzformen fuer `set`, `clear`, `update` und `emit` sind vorhanden.
Quellenverwaltung, Servicebetrieb und die vorlaeufigen
anwendungsspezifischen Kompatibilitaetskommandos bleiben zusaetzlich
verfuegbar.

## API

V2:

- `GET /api/v2/states`
- `GET /api/v2/overlays`
- `GET /api/v2/events`
- `GET /api/v2/presets`
- `GET /api/v2/show/{target:path}`
- `POST /api/v2/set/state`
- `POST /api/v2/clear/state`
- `POST /api/v2/set/overlay`
- `POST /api/v2/update/overlay`
- `POST /api/v2/clear/overlay`
- `POST /api/v2/emit/event`

Allgemein und vorlaeufige Kompatibilitaet:

- `GET /`
- `GET /health`
- `GET /api/v1/ping`
- `GET /api/v1/status`
- V1-Quellenverwaltung
- einzelne V1-Anwendungs-Callbacks fuer State, Countdown, Richtung und Output

## Prozessstart

- `main.py` und `src/__main__.py` delegieren an `src.interfaces.cli.main()`
- `serve` erstellt die FastAPI-App ueber `src.interfaces.api.create_app()`
- `create_app()` startet den Render-Worker im Lifespan
- die Standardbibliothek wird aus `default-effects.lefxset` geladen
- nur der Background-State wird persistiert
