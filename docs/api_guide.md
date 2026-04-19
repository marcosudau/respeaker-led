# CLI Und API

Diese Seite beschreibt die oeffentliche Steuerung des laufenden Services in `src/`.

Sie ist richtig fuer dich, wenn du:

- den Service starten willst
- einen laufenden Service per CLI fernsteuern willst
- denselben Service per HTTP ansteuern willst
- eingebaute Effekte direkt auf Runtime-Layer legen willst

## Kurzfassung

- Die API steuert einen laufenden Service in `src/`
- Die CLI kann den Service starten oder mit ihm sprechen
- `list-effects` und `apply-effect` arbeiten gegen denselben laufenden Service
- Effekt-Presets und Commands bleiben optional und laufen innerhalb desselben Dienstes
- Release 1 ist auf den lokalen Unterprozess-Betrieb ausgelegt

## Service starten

```powershell
python .\main.py serve --host 127.0.0.1 --port 8765
```

Optional mit Portpool:

```powershell
python .\main.py serve --host 127.0.0.1 --port 8765 --port-pool 8765-8770
```

Hinweis:

- `--no-device` ist nur fuer den Startbefehl relevant.
- Alle anderen CLI-Kommandos sprechen den laufenden Service ueber HTTP an.
- Vor dem Start wird die Portverfuegbarkeit geprueft.
- Wenn `--port-pool` gesetzt ist, kann der Service auf einen freien Port aus dieser Liste ausweichen.
- Der effektiv verwendete Host und Port werden als JSON auf stdout und in `active_service.json` im Temp-Verzeichnis des Service ausgegeben.
- Es ist genau eine aktive Instanz vorgesehen; eine neu gestartete Instanz versucht eine alte aktive Instanz zuerst zu beenden.

## Wichtige lokale CLI-Befehle

### Service fernsteuern

```powershell
python .\main.py list-effects
python .\main.py list-effect-sources
python .\main.py list-effect-presets default-effects::soft_pulse
python .\main.py list-commands --source default-effects
python .\main.py ping
python .\main.py status
python .\main.py set-state listening
python .\main.py clear-state
python .\main.py apply-effect solid_color main --params '{"color":"0x224466"}'
python .\main.py clear-layer main
python .\main.py emit-event trigger_received --duration-ms 900 --source manual
python .\main.py start-countdown 5000 --remaining-ms 2000 --follow-up-state transcribing
python .\main.py update-countdown 1200
python .\main.py cancel-countdown
python .\main.py set-direction 120
python .\main.py clear-direction
python .\main.py set-brightness 0.5
python .\main.py set-enabled false
python .\main.py apply-effect-preset default-effects::effect_soft_pulse_main
python .\main.py invoke-command default-effects effect_soft_pulse_accent
```

## Runtime-Dateien

Wichtige Dateien im laufenden Unterprozess-Modell:

- `active_service.json` im Temp-Verzeichnis des Service mit PID, Host, Port, Status und Logdatei der aktiven Instanz
- `background_state.json` im Temp-Verzeichnis des Service fuer den persistierten Background-State
- `logs/led_controller.log` fuer das einfache Basislogging

Die Host-Anwendung kann `active_service.json` verwenden, um bei Portpool-Fallback den effektiv gestarteten Port zu erfahren.

## Fuer `apply-effect` relevante Layernamen

Folgende Kurzformen akzeptieren CLI und API:

- `background`
- `state`
- `main`
- `temp_overlay`
- `ongoing_overlay`
- `event`

Ebenso funktionieren die vollstaendigen Enum-Namen wie `MAIN_LAYER` oder `EVENT_LAYER`.

## HTTP-Routen

### Basisrouten

- `GET /`
- `GET /docs`
- `GET /health`
- `GET /api/v1/ping`
- `GET /api/v1/status`
- `GET /api/v1/effects`

### Presets

- `GET /api/v1/presets`
- `GET /api/v1/presets/{preset_id}`
- `GET /api/v1/presets/{preset_id}/sample`
- `POST /api/v1/presets/{preset_id}/activate`

### Kommandorouten

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

## Beispiel-Requests

### Status lesen

```http
GET /api/v1/status
```

### Basiszustand setzen

```http
POST /api/v1/commands/set_state
Content-Type: application/json
```

```json
{
  "state_name": "listening",
  "payload": {
    "source": "manual"
  }
}
```

### Effektliste lesen

```http
GET /api/v1/effects
```

### Effekt direkt setzen

```http
POST /api/v1/commands/apply_effect
Content-Type: application/json
```

```json
{
  "effect_id": "solid_color",
  "target_layer": "main",
  "params": {
    "color": "0x224466"
  }
}
```

### Layer leeren

```http
POST /api/v1/commands/clear_layer
Content-Type: application/json
```

```json
{
  "target_layer": "main"
}
```

### Event ausloesen

```http
POST /api/v1/commands/emit_event
Content-Type: application/json
```

```json
{
  "event_name": "trigger_received",
  "payload": {
    "duration_ms": 900,
    "source": "manual"
  }
}
```

### Countdown starten

```http
POST /api/v1/commands/start_timeout_countdown
Content-Type: application/json
```

```json
{
  "total_ms": 5000,
  "remaining_ms": 2000,
  "follow_up_state": "transcribing",
  "payload": {
    "source": "stt",
    "reason": "vad_timeout"
  }
}
```

### Richtung setzen

```http
POST /api/v1/commands/set_direction
Content-Type: application/json
```

```json
{
  "direction": 120
}
```

## Wann ist dieser Weg richtig?

- wenn ein anderer Prozess den Controller steuern soll
- wenn du HTTP als Integrationsschnittstelle brauchst
- wenn der Controller dauerhaft laufen und seinen Zustand behalten soll
- wenn du den Service-Kern mit Layern, Events, Countdowns und direkten Effektkommandos nutzen willst

## Weiterfuehrende Seiten

- [Aktueller Ansatz im Repo](current_approach.md)
- [Schnellstart in einzelnen Schritten](getting_started.md)
- [Effekte verstehen und neue Effekte bauen](effects.md)
- [Entwickler-Schnittstellen](dev/public_entry_points.md)
