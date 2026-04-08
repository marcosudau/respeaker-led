# Public Entry Points

Stand: nach Abschluss der Architektur-Refaktorisierung.

## Baseline Test Command

```powershell
pytest -q
```

## Runtime Controller

Oeffentliche Methoden von `src.runtime.ControllerRuntime`:

- `set_state(state_name, payload=None, timestamp=None)`
- `clear_state(state_name=None, timestamp=None)`
- `emit_event(event_name, payload=None, timestamp=None)`
- `start_timeout_countdown(total_ms, remaining_ms=None, follow_up_state=None, payload=None, timestamp=None)`
- `update_timeout_countdown(remaining_ms, timestamp=None)`
- `cancel_timeout_countdown()`
- `set_direction(direction_deg)`
- `clear_direction()`
- `set_brightness(level)`
- `set_enabled(enabled)`
- `reset(initial_state="idle")`
- `apply_preset(preset_id, spec)`
- `apply_preset_from_file(preset_id, spec_file)`
- `set_progress(value, color=0x3399FF, base_color=0x03070B)`
- `render_once(now=None)`
- `run(seconds=None, fps=12.0, tick=None)`
- `get_status(now=None)`
- `close()`

Alias fuer Kompatibilitaet:

- `src.runtime.LedController`

## Service Wrapper

Oeffentliche Methoden von `src.service.ControllerService`:

- `start()`
- `stop()`
- `ping()`
- `get_status()`
- `snapshot()`
- `set_state(...)`
- `clear_state(...)`
- `emit_event(...)`
- `reset()`
- `shutdown()`
- `start_timeout_countdown(...)`
- `update_timeout_countdown(...)`
- `cancel_timeout_countdown()`
- `set_direction(...)`
- `clear_direction()`
- `set_brightness(...)`
- `set_enabled(...)`
- `list_presets()`
- `preset_info(preset_id)`
- `preset_sample(preset_id)`
- `activate_preset(preset_id, spec)`

## Local Client

Oeffentliche Methoden von `src.client.LocalControllerClient`:

- `ping()`
- `get_status()`
- `set_state(...)`
- `clear_state(...)`
- `emit_event(...)`
- `reset()`
- `shutdown()`
- `start_timeout_countdown(...)`
- `update_timeout_countdown(...)`
- `cancel_timeout_countdown()`
- `set_direction(...)`
- `clear_direction()`
- `set_brightness(...)`
- `set_enabled(...)`
- `activate_preset(...)`

Der Client ist standardmaessig Best-Effort und wirft nur dann Exceptions, wenn `best_effort=False` gesetzt wird.

## STT Adapter

Oeffentliche Methoden von `src.stt_adapter.SttLedAdapter`:

- `on_vad_detect_start(...)`
- `on_recording_start(...)`
- `on_turn_detection_start(...)`
- `on_turn_detection_stop(...)`
- `on_recording_stop(...)`
- `on_transcription_start(...)`
- `on_text_committed(...)`
- `on_wakeword_detection_start(...)`
- `on_wakeword_detected(...)`
- `on_wakeword_detection_end(...)`

## CLI Commands

Globale Optionen:

- `--no-device`
- `--fps <float>`

Kommandos:

- `list-presets`
- `serve`
- `ping`
- `status`
- `set-state`
- `clear-state`
- `emit-event`
- `start-countdown`
- `update-countdown`
- `cancel-countdown`
- `set-direction`
- `clear-direction`
- `set-brightness`
- `set-enabled`
- `reset`
- `shutdown`
- `activate-preset`
- `demo`

## API Routes

Allgemein:

- `GET /`
- `GET /health`
- `GET /api/v1/ping`
- `GET /api/v1/status`

Preset-Discovery:

- `GET /api/v1/presets`
- `GET /api/v1/presets/{preset_id}`
- `GET /api/v1/presets/{preset_id}/sample`
- `POST /api/v1/presets/{preset_id}/activate`

Controller-Kommandos:

- `POST /api/v1/commands/set_state`
- `POST /api/v1/commands/clear_state`
- `POST /api/v1/commands/emit_event`
- `POST /api/v1/commands/reset`
- `POST /api/v1/commands/shutdown`
- `POST /api/v1/commands/start_timeout_countdown`
- `POST /api/v1/commands/update_timeout_countdown`
- `POST /api/v1/commands/cancel_timeout_countdown`
- `POST /api/v1/commands/set_direction`
- `POST /api/v1/commands/clear_direction`
- `POST /api/v1/commands/set_brightness`
- `POST /api/v1/commands/set_enabled`

## Prozess-Startpfad

- `main.py` und `src/__main__.py` delegieren an `src.cli.main()`
- `python .\main.py serve` baut die FastAPI-App ueber `src.api.create_app()`
- `create_app()` haengt `ControllerService` an den App-State und startet den Render-Worker im Lifespan

Hinweis:

- Discovery bleibt optional.
- Ohne Preset-Packs liefert `GET /api/v1/presets` eine leere Liste.
- Bei fehlender Hardware faellt der Service sicher auf Console-Preview zurueck.
