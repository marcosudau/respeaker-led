# Bedienung ueber CLI und HTTP API

CLI und HTTP API transportieren dieselben Steuerungskommandos. Die kanonische
Grammatik beantwortet zuerst, was getan wird, und danach, mit welchem Objekt.

## Kanonische Kommandos

```text
ledctl set state <id-or-preset>
ledctl clear state

ledctl set overlay <id-or-preset> --channel <name>
ledctl update overlay <channel>
ledctl clear overlay <channel>

ledctl emit event <id-or-preset>
```

Im Repository wird `ledctl` durch `python .\main.py` repraesentiert.

## State

```powershell
python .\main.py set state rotating_segment `
  --config '{"color":"blue","speed":1.2}'
python .\main.py clear state
```

`set` ist idempotent: Ohne Modus stellt es sicher, dass das Ziel aktiv ist.

## Controlled Overlay

```powershell
python .\main.py set overlay direction_indicator `
  --channel doa `
  --config '{"color":"green"}' `
  --inputs '{"direction_deg":120}'

python .\main.py update overlay doa `
  --inputs '{"direction_deg":240}'

python .\main.py clear overlay doa
```

Timed Overlays werden einmal ohne Channel aktiviert und enden automatisch.
Controlled Overlays benoetigen einen Channel.

## Event

```powershell
python .\main.py emit event short_pulse `
  --config '{"color":"blue","duration_ms":"600ms"}'
```

Events unterstuetzen kein nachtraegliches Update und keinen
Aktivierungsmodus.

## Aktivierungsmodus

Fuer State und Controlled Overlay:

| Modus | Bedeutung |
|---|---|
| kein Modus oder `--on` | Ziel sicher aktivieren |
| `--off` | Ziel sicher deaktivieren |
| `--toggle` | aktuellen Zustand ausdruecklich umschalten |

Ein implizites Toggle waere fuer wiederholte API-Aufrufe und Retries
unsicher. Deshalb bedeutet ein blosses `set` immer `on`.

## Lesen

```powershell
python .\main.py list states
python .\main.py list overlays
python .\main.py list events
python .\main.py list presets
python .\main.py show rotating_segment
```

Standardlisten enthalten nur IDs und bleiben kurz:

```json
["fill_ring","rotating_segment","yin_yang_spin"]
```

- `--json`: kompakte maschinenlesbare CLI-Ausgabe
- `--details`: vollstaendige Metadaten aller Listeneintraege
- `show`: vollstaendige Details eines Ziels

Die HTTP API liefert immer JSON.

## HTTP-Endpunkte

```text
GET  /api/v2/states
GET  /api/v2/overlays
GET  /api/v2/events
GET  /api/v2/presets
GET  /api/v2/show/{target:path}

POST /api/v2/set/state
POST /api/v2/clear/state
POST /api/v2/set/overlay
POST /api/v2/update/overlay
POST /api/v2/clear/overlay
POST /api/v2/emit/event
```

Sammlungen akzeptieren `?details=true`. Mutationspayloads trennen `config`
und `inputs`. Der Aktivierungsmodus steht als explizites `action` mit
`on`, `off` oder `toggle` im Payload.

## Fehlertoleranz

Dokumentiert werden nur die vollstaendigen kanonischen Formen. Die CLI darf
eine eindeutige Kurzform akzeptieren und meldet danach die kanonische
Schreibweise.

Robustheit bedeutet nicht Raten:

- eindeutige Aliase werden normalisiert,
- unbekannte Felder liefern konkrete Feldfehler,
- aehnliche IDs werden vorgeschlagen,
- unscharfe Treffer werden nicht automatisch ausgefuehrt,
- ein ungueltiges Kommando veraendert keinen Runtime-Zustand.

Vollstaendige Referenzen:

- [CLI mit allen Kommandos und Optionen](../cli_guide.md)
- [HTTP API mit allen Endpunkten und Payloads](../api_guide.md)
