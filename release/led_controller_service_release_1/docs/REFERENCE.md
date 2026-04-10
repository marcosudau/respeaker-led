# Referenz

## CLI-Kommandos

Der Release-Build enthaelt diese 20 oeffentlichen Kommandos:

- `serve`
- `ping`
- `status`
- `list-effects`
- `list-presets`
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
- `activate-preset`

## Wichtige HTTP-Routen

Basis:

- `GET /`
- `GET /health`
- `GET /api/v1/ping`
- `GET /api/v1/status`
- `GET /api/v1/effects`

Presets:

- `GET /api/v1/presets`
- `GET /api/v1/presets/{preset_id}`
- `GET /api/v1/presets/{preset_id}/sample`
- `POST /api/v1/presets/{preset_id}/activate`

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

## Layernamen fuer `apply-effect`

Kurzformen:

- `background`
- `state`
- `main`
- `temp_overlay`
- `ongoing_overlay`
- `event`

Auch gueltig sind die Enum-Namen:

- `BACKGROUND_STATE_LAYER`
- `STATE_LAYER`
- `MAIN_LAYER`
- `TEMP_OVERLAY_LAYER`
- `ONGOING_OVERLAY_LAYER`
- `EVENT_LAYER`

## Eingebaute Effekte

### `blink_color`

- Beschreibung: Blinkt zwischen Akzent- und Grundfarbe.
- Layer: `STATE_LAYER`, `MAIN_LAYER`, `TEMP_OVERLAY_LAYER`, `ONGOING_OVERLAY_LAYER`, `EVENT_LAYER`
- Parameter:
  `color` als Farbe, Default `#FFAA00`
  `base_color` als Farbe, Default `#000000`
  `period_ms` als Dauer in Millisekunden, Default `900`
  `duty_cycle` als Float zwischen `0` und `1`, Default `0.5`

### `countdown_ring`

- Beschreibung: Stellt einen Countdown als temporaeren Overlay-Effekt dar.
- Layer: `TEMP_OVERLAY_LAYER`
- Parameter:
  `total_ms` als Dauer in Millisekunden, Default `1000`
  `deadline_ts` als Float-Timestamp, optional
  `color` als Farbe, Default `#FF9F1A`
  `marker_color` als Farbe, Default `#FFF3D1`

### `direction_indicator`

- Beschreibung: Markiert eine Richtung als halbtransparente Ring-Einblendung.
- Layer: `ONGOING_OVERLAY_LAYER`
- Parameter:
  `direction_deg` als Winkel, Default `0`
  `center_color` als Farbe, Default `#EAF8FF`
  `side_color` als Farbe, Default `#7FC9FF`

### `legacy_visual`

- Beschreibung: Kompatibilitaetshueller fuer bestehende Visual-Objekte.
- Layer: alle Layer
- Parameter: keine

### `off`

- Beschreibung: Schaltet alle LEDs des Ziel-Layers aus.
- Layer: `BACKGROUND_STATE_LAYER`, `STATE_LAYER`, `MAIN_LAYER`
- Parameter: keine

### `progress_bar`

- Beschreibung: Bildet einen Fortschritt ringfoermig ab.
- Layer: `MAIN_LAYER`, `TEMP_OVERLAY_LAYER`
- Parameter:
  `value` als Float zwischen `0` und `100`, Default `0`
  `color` als Farbe, Default `#33AAFF`
  `base_color` als Farbe, Default `#050505`

### `soft_pulse`

- Beschreibung: Weiches Pulsieren zwischen Grund- und Akzentfarbe.
- Layer: `BACKGROUND_STATE_LAYER`, `STATE_LAYER`, `MAIN_LAYER`
- Parameter:
  `color` als Farbe, Default `#33AAFF`
  `base_color` als Farbe, Default `#050A0F`
  `period_ms` als Dauer in Millisekunden, Default `1800`

### `solid_color`

- Beschreibung: Faerbt den gesamten Ziel-Layer statisch ein.
- Layer: `BACKGROUND_STATE_LAYER`, `STATE_LAYER`, `MAIN_LAYER`, `TEMP_OVERLAY_LAYER`, `ONGOING_OVERLAY_LAYER`
- Parameter:
  `color` als Farbe, Default `#33AAFF`
  `brightness` als Float zwischen `0` und `1`, Default `1.0`

### `warning_flash`

- Beschreibung: Kurzer Warnblitz fuer den Event-Layer.
- Layer: `EVENT_LAYER`
- Parameter:
  `color` als Farbe, Default `#FFAA00`
  `base_color` als Farbe, Default `#120400`
  `period_ms` als Dauer in Millisekunden, Default `400`
  `duty_cycle` als Float zwischen `0` und `1`, Default `0.5`

## Aktueller Preset-Stand

Im geprueften Release meldet `list-presets` aktuell keine Presets. Die Preset-Schnittstelle bleibt aber vorhanden und kann spaeter mit optionalen Packs erweitert werden.

## Wichtige Laufzeitdateien

- `runtime_state/active_service.json`: aktive Instanz mit PID, Host, Port und Status
- `runtime_state/background_state.json`: persistierter Background-State
- `logs/led_controller.log`: Basislogging