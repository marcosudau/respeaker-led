# CLI Und API

Diese Seite ist nur fuer den Fall gedacht, dass du einen **laufenden Controller-Prozess** von aussen steuern willst.

Wenn du nur lokal Effekte bauen oder JSON/YAML laden willst, bist du hier falsch. Dann geh zu:

- [Eigene Anzeigen Schritt fuer Schritt](effects_engine_tutorial.md)
- [Farben, Typen und Namen zum Nachschlagen](reference.md)

## Das Wichtigste Vorweg

- Die API steuert einen laufenden Service
- Die CLI spricht mit diesem Service oder startet ihn
- JSON/YAML-Dateien werden **nicht** an diese API geschickt

## Server starten

```powershell
python .\main.py --no-device serve --host 127.0.0.1 --port 8765
```

## Typische CLI-Befehle

```powershell
python .\main.py status
python .\main.py set-state listening
python .\main.py emit-event trigger_received --duration-ms 900 --source manual
python .\main.py start-countdown 5000 --remaining-ms 2000 --follow-up-state transcribing
python .\main.py set-direction 120
```

## Typische API-Requests

### Zustand lesen

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
  "direction_deg": 120
}
```

## Wann ist die API der richtige Weg?

- wenn ein anderer Prozess den Controller steuern soll
- wenn du einen lokalen Service laufen hast
- wenn du HTTP als Integrationsschnittstelle brauchst

## Wann ist die API nicht der richtige Weg?

- wenn du nur kurz einen Effekt lokal anzeigen willst
- wenn du JSON/YAML-Effektdateien laden willst
- wenn du die Effects Engine direkt in Python benutzt

## Mehr Details

- Nutzer-Referenz: [reference.md](reference.md)
- Entwickler-Schnittstellen: [dev/public_entry_points.md](dev/public_entry_points.md)
