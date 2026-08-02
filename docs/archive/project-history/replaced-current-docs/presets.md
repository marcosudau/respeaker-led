# Presets

Ein LEFX-V2-Preset ist eine benannte, wiederverwendbare Konfiguration fuer
genau eine State-, Overlay- oder Event-Definition.

## Vertrag

Ein Preset darf:

- eine Definition referenzieren
- deklarierte `config`-Werte vorbelegen
- eine eigene global eindeutige ID und Metadaten besitzen

Ein Preset darf nicht:

- den Effekttyp oder internen Layer aendern
- Lebenszyklus, Dauer oder Queue-Verhalten aendern
- Runtime-Eingaben festschreiben
- eigene Befehlslogik enthalten

Damit bleibt ein Preset eine reine Konfiguration. `commands.json` und
eingebettete On-/Off-/Toggle-Commands gehoeren nicht zum V2-Modell.

## Discovery

```powershell
python .\main.py list presets
python .\main.py list presets --details
python .\main.py show <preset-id>
```

API:

- `GET /api/v2/presets`
- `GET /api/v2/presets?type=state|overlay|event`
- `GET /api/v2/presets?details=true`
- `GET /api/v2/show/{preset-id}`

## Anwendung

Ein Preset wird an jeder Stelle akzeptiert, an der auch eine Definition
akzeptiert wird:

```powershell
python .\main.py set state <preset-id>
python .\main.py set overlay <preset-id> --channel <name>
python .\main.py emit event <preset-id>
```

Der Typ wird aus der referenzierten Definition ermittelt. Falsche Verwendung,
beispielsweise ein Event-Preset bei `set state`, wird abgewiesen.
