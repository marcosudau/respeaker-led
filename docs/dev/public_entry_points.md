# Public Entry Points

Stand: nach finalem LEFX-Artefakt-Cleanup.

## Baseline Commands

```powershell
pytest -q
python .\tools\effect_building\build_lefxset.py --rebuild-packages
```

## Runtime Controller

Oeffentliche Methoden von `src.engine.runtime.ControllerRuntime`:

- `set_state(state_name, payload=None, timestamp=None)`
- `clear_state(state_name=None, timestamp=None)`
- `emit_event(event_name, payload=None, timestamp=None)`
- `start_timeout_countdown(total_ms, remaining_ms=None, follow_up_state=None, payload=None, timestamp=None)`
- `update_timeout_countdown(remaining_ms, timestamp=None)`
- `cancel_timeout_countdown()`
- `set_direction(direction)`
- `clear_direction()`
- `set_brightness(level)`
- `set_enabled(enabled)`
- `reset(initial_state="idle")`
- `set_progress(value, color=0x3399FF, background_color=0x03070B)`
- `apply_effect(effect_id, target_layer, params=None, ...)`
- `apply_effect_preset(source_id, preset_id, ...)`
- `clear_layer(target_layer)`
- `is_command_active(source_id, command_name, target_layer)`
- `apply_default_background_state()`
- `restore_persisted_background_state(persisted_state)`
- `background_state_signature()`
- `background_state_persistence_snapshot()`
- `render_once(now=None)`
- `run(seconds=None, fps=12.0, tick=None)`
- `get_status(now=None)`
- `close()`

## Service Wrapper

Oeffentliche Methoden von `src.services.service.ControllerService`:

- `start()`
- `stop()`
- `set_shutdown_callback(callback)`
- `snapshot()`
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
- `list_effects()`
- `list_effects_for_source(source_id)`
- `effect_info(effect_id)`
- `effect_info_for_source(source_id, effect_id)`
- `list_effect_presets(source_id=None, effect_id=None)`
- `effect_preset_info(source_id, preset_id)`
- `list_effect_sources()`
- `register_effect_source(path, enabled=True)`
- `reload_effect_sources()`
- `remove_effect_source(source_id)`
- `list_effect_commands(source_id=None)`
- `list_effect_commands_for_effect(source_id, effect_id)`
- `effect_command_info(source_id, command_name)`
- `apply_effect(effect_id, target_layer, params=None, ...)`
- `clear_layer(target_layer)`
- `invoke_effect_command(source_id, command_name, state=None)`
- `apply_effect_preset(source_id, preset_id)`

## Local Client

Oeffentliche Methoden von `src.interfaces.client.LocalControllerClient`:

- `ping()`
- `get_status()`
- `list_effects()`
- `list_effects_for_source(source_id)`
- `get_effect(source_id, effect_id)`
- `list_effect_presets(source_id, effect_id)`
- `list_effect_commands_for_effect(source_id, effect_id)`
- `apply_effect_for_source(source_id, effect_id, target_layer, params=None, ...)`
- `get_effect_preset(source_id, preset_id)`
- `apply_effect_preset(source_id, preset_id)`
- `list_effect_sources()`
- `register_effect_source(path, enabled=True)`
- `reload_effect_sources()`
- `remove_effect_source(source_id)`
- `list_commands(source_id=None)`
- `get_command(source_id, command_name)`
- `invoke_command(source_id, command_name, state=None)`
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
- `apply_effect(...)`
- `clear_layer(...)`

Der Client ist standardmaessig Best-Effort und wirft nur dann Exceptions, wenn `best_effort=False` gesetzt wird.

## STT Adapter

Oeffentliche Methoden von `src.integrations.stt_adapter.SttLedAdapter`:

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

- `list-effects`
- `show-effect`
- `list-effect-presets`
- `list-effect-commands`
- `apply-effect-preset`
- `list-effect-sources`
- `register-effect-source`
- `reload-effect-sources`
- `remove-effect-source`
- `list-commands`
- `invoke-command`
- `serve`
- `ping`
- `status`
- `set-state`
- `clear-state`
- `emit-event`
- `apply-effect`
- `clear-layer`
- `reset`
- `shutdown`
- `start-countdown`
- `update-countdown`
- `cancel-countdown`
- `set-direction`
- `clear-direction`
- `set-brightness`
- `set-enabled`

## API Routes

Allgemein:

- `GET /`
- `GET /health`
- `GET /api/v1/ping`
- `GET /api/v1/status`

Effekte und Effektquellen:

- `GET /api/v1/effects`
- `GET /api/v1/effects/{source_id}`
- `GET /api/v1/effects/{source_id}/{effect_id}`
- `GET /api/v1/effects/{source_id}/{effect_id}/presets`
- `GET /api/v1/effects/{source_id}/{effect_id}/commands`
- `POST /api/v1/effects/{source_id}/{effect_id}/apply`
- `GET /api/v1/effect-presets/{source_id}/{preset_id}`
- `POST /api/v1/effect-presets/{source_id}/{preset_id}/apply`
- `GET /api/v1/effect-sources`
- `POST /api/v1/effect-sources/register`
- `POST /api/v1/effect-sources/reload`
- `DELETE /api/v1/effect-sources/{source_id}`

Kommandos:

- `POST /api/v1/commands/set_state`
- `POST /api/v1/commands/clear_state`
- `POST /api/v1/commands/emit_event`
- `POST /api/v1/commands/apply_effect`
- `POST /api/v1/commands/clear_layer`
- `POST /api/v1/commands/reset`
- `POST /api/v1/commands/shutdown`
- `POST /api/v1/commands/start_timeout_countdown`
- `POST /api/v1/commands/update_timeout_countdown`
- `POST /api/v1/commands/cancel_timeout_countdown`
- `POST /api/v1/commands/set_direction`
- `POST /api/v1/commands/clear_direction`
- `POST /api/v1/commands/set_brightness`
- `POST /api/v1/commands/set_enabled`
- `GET /api/v1/commands`
- `GET /api/v1/commands/{source_id}`
- `GET /api/v1/commands/{source_id}/{command_name}`
- `POST /api/v1/commands/{source_id}/{command_name}`
- `POST /api/v1/commands/{source_id}/{command_name}/on`
- `POST /api/v1/commands/{source_id}/{command_name}/off`

## Prozess-Startpfad

- `main.py` und `src/__main__.py` delegieren an `src.interfaces.cli.main()`
- `python .\src\interfaces\cli.py ...` funktioniert ebenfalls als direkter Skriptstart
- `python .\main.py serve` baut die FastAPI-App ueber `src.interfaces.api.create_app()`
- `create_app()` haengt `ControllerService` an den App-State und startet den Render-Worker im Lifespan

Hinweis:

- Die Default-Effektbibliothek wird aus `default-effects.lefxset` geladen, nicht aus rohen Python-Quellen.
- Der Service persistiert `BACKGROUND_STATE_LAYER` in `background_state.json` im Temp-Verzeichnis `respeaker_led_controller_runtime_state/` und restauriert ihn beim Start.
- Bei fehlender Hardware faellt der Service sicher auf Console-Preview zurueck.
