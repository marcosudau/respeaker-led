# Schnellstart: Service Starten Und Effekte Setzen

Diese Anleitung fuehrt dich in einzelnen Schritten durch den heute aktiven Betriebsweg.

Voraussetzung:

- du befindest dich im Projekt-Root
- du verwendest eine Python-Umgebung, in der die Projektabhaengigkeiten bereits funktionieren

## 1. Erstes Terminal oeffnen und den Service starten

Empfohlen fuer den ersten Test ohne Hardware:

```powershell
python .\main.py --no-device serve --host 127.0.0.1 --port 8765
```

Optional fuer einen Unterprozess-Betrieb mit Portpool:

```powershell
python .\main.py --no-device serve --host 127.0.0.1 --port 8765 --port-pool 8765-8770
```

Wichtig:

- dieses Terminal bleibt offen
- der Prozess rendert jetzt laufend Frames
- im `--no-device`-Modus werden die Frames in der Konsole als Preview ausgegeben
- beim Start gibt der Prozess eine JSON-Zeile mit dem effektiv verwendeten Host und Port aus
- dieselben Laufzeitdaten stehen auch in `active_service.json` im Temp-Verzeichnis `respeaker_led_controller_runtime_state/`

## 2. Zweites Terminal oeffnen und pruefen, ob der Service erreichbar ist

```powershell
python .\main.py ping
python .\main.py status
```

Wenn alles laeuft, bekommst du JSON-Antworten zurueck.

## 3. Verfuegbare Effekte anzeigen

```powershell
python .\main.py list-effects
```

Du bekommst eine Liste aller eingebauten Effekte mit IDs, Parametern und unterstuetzten Layern.

Wenn du verstehen willst, wie diese Effekte intern aufgebaut sind oder selbst neue schreiben willst:

- [Effekte verstehen und neue Effekte bauen](effects.md)

## 4. Einen ersten Effekt auf den Haupt-Layer legen

```powershell
python .\main.py apply-effect solid_color main --params '{"color":"0x224466"}'
```

Das setzt eine feste Farbe auf den Haupt-Layer.

Zur Kontrolle kannst du direkt danach den Status lesen:

```powershell
python .\main.py status
```

## 5. Einen animierten Effekt auf den State-Layer setzen

```powershell
python .\main.py apply-effect soft_pulse state --params '{"color":"0x33AAFF","background_color":"0x02060A","period_ms":1600}'
```

Damit laeuft ein pulsierender Hintergrundzustand.

## 6. Kurzlebiges Event ausloesen

```powershell
python .\main.py emit-event trigger_received --duration-ms 900 --source manual
```

Das Event landet im Event-Layer und verschwindet nach seiner Laufzeit wieder.

## 7. Weitere typische Steuerbefehle testen

```powershell
python .\main.py set-state listening
python .\main.py set-direction 120
python .\main.py start-countdown 5000 --remaining-ms 2000 --follow-up-state transcribing
```

## 8. Einen Layer wieder leeren

```powershell
python .\main.py clear-layer main
python .\main.py clear-direction
python .\main.py cancel-countdown
```

## 9. Optional Effekt-Presets oder Commands nutzen

Verfuegbare Effektquellen und Presets anzeigen:

```powershell
python .\main.py list-effect-sources
python .\main.py list-effect-presets default-effects::soft_pulse
python .\main.py list-commands --source default-effects
```

Ein eingebettetes Effekt-Preset oder einen Command ausloesen:

```powershell
python .\main.py apply-effect-preset default-effects::effect_soft_pulse_main
python .\main.py invoke-command default-effects effect_soft_pulse_accent
```

## 10. Service sauber beenden

```powershell
python .\main.py shutdown
```

## Wenn etwas nicht klappt

- [CLI und API im Detail](api_guide.md)
- [Effekte verstehen und neue Effekte bauen](effects.md)
- [Troubleshooting](troubleshooting.md)
- [Aktueller Ansatz im Repo](current_approach.md)
