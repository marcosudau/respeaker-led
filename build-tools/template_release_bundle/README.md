# LED Controller Service Release 1

Dieses Verzeichnis dient im Repo als Vorlage fuer das Release-1-Bundle. Beim eigentlichen Release-Build wird die lokale Windows-EXE in diese Struktur eingesetzt.

## Inhalt des erzeugten Bundles

- `led_controller_service_<version>.exe` oder `led_controller_service.exe`: die startbare Anwendung, je nach Build-Flag
- `docs/HOST_APP_INTEGRATION.md`: Einbindung in eine Host-App
- `docs/REFERENCE.md`: Effekte, Befehle, Layer und HTTP-Routen
- `examples/led_controller_host.py`: direkt nutzbares Python-Modul fuer Start, Port-Erkennung und Steuerung
- `examples/example_usage.py`: kleines Integrationsbeispiel

## Gepruefter Startstatus

Am 10.04.2026 wurde diese EXE in zwei Modi geprueft:

- ohne Hardware ueber `--no-device`
- mit echter Hardware im Geraetemodus

Der Hardwaretest hat einen laufenden Dienst mit `output_mode=device` und `device_available=true` bestaetigt.

## Schnellstart im erzeugten Bundle

### Manuell starten

```powershell
.\<exe_name>.exe --serve
```

Der Dienst schreibt beim Start eine JSON-Zeile auf stdout, zum Beispiel:

```json
{"event":"service_binding","host":"127.0.0.1","port":8765,"requested_port":8765,"port_pool":[8765,8766,8767,8768,8769,8770],"status":"binding"}
```

Die Host-App soll diese Zeile lesen und den effektiven Port daraus verwenden.

`<exe_name>.exe` ist standardmaessig `led_controller_service_<version>.exe`. Nur bei Builds mit `--no-version` heisst die Datei `led_controller_service.exe`.

### Default-Verhalten

- Standard-Host: `127.0.0.1`
- Standard-Port: `8765`
- Standard-Portpool ohne eigene Angabe: `8765-8770`
- Es gibt immer nur eine aktive Instanz; ein neuer Start versucht eine alte Instanz zuerst zu beenden.

## Laufzeitdateien

Diese Dateien entstehen zur Laufzeit:

- `logs/led_controller.log` im App-Verzeichnis neben der EXE
- `background_state.json` im Temp-Verzeichnis des Service unter `respeaker_led_controller_runtime_state/`
- `active_service.json` nur waehrend eine Instanz laeuft, ebenfalls im Temp-Verzeichnis des Service

## Naechster Einstieg

Wenn die EXE aus einer Host-App gesteuert werden soll, beginne mit `docs/HOST_APP_INTEGRATION.md` und `examples/led_controller_host.py`.
