# Host-App-Integration

Diese Release-Version ist fuer eine lokale Host-Anwendung gedacht, die die EXE als Unterprozess startet und danach per HTTP steuert.

## Empfohlenes Integrationsmodell

1. Die Host-App startet `led_controller_service.exe` als Unterprozess.
2. Die Host-App liest stdout, bis die JSON-Zeile mit `event=service_binding` erscheint.
3. Ab dann verwendet die Host-App den darin gemeldeten Host und Port fuer alle HTTP-Aufrufe.
4. Beim Beenden schickt die Host-App den Shutdown-Befehl an den Dienst.

## Warum stdout wichtig ist

Der Dienst kann auf einen freien Port aus dem Portpool ausweichen. Deshalb darf die Host-App nicht nur den angeforderten Port annehmen, sondern muss den effektiv gestarteten Port aus der `service_binding`-Zeile verwenden.

Zusatz-Fallback:

- Waehren der Laufzeit liegt dieselbe Information in `runtime_state/active_service.json` neben der EXE.

## Startbeispiel

```powershell
.\led_controller_service.exe --serve
```

Optional mit explizitem Port und Portpool:

```powershell
.\led_controller_service.exe --serve --host 127.0.0.1 --port 8891 --port-pool 8891-8893
```

Die bisherige Schreibweise `--serve` wird weiterhin akzeptiert. Intern startet sie denselben `serve`-Pfad.

## Python-Modul im Paket

Das Modul `examples/led_controller_host.py` kapselt den empfohlenen Weg bereits:

- Start der EXE per `subprocess.Popen`
- Lesen der `service_binding`-Zeile von stdout
- Fallback auf `runtime_state/active_service.json`
- HTTP-Steuerung ohne externe Python-Abhaengigkeiten
- sauberes Beenden ueber den Shutdown-Endpunkt

## Typischer Ablauf in der Host-App

```python
from pathlib import Path

from led_controller_host import LedControllerRelease1


package_root = Path(__file__).resolve().parent
controller = LedControllerRelease1(package_root / "led_controller_service.exe")

binding = controller.start(use_device=True)
print(binding)

controller.apply_effect("solid_color", "main", {"color": "#224466"})
status = controller.status()
print(status)

controller.close()
```

## Wichtige Laufzeiteigenschaften

- Startsignal: drei schnelle gruene Vollring-Blinks
- Stopsignal: drei schnelle rote Vollring-Blinks
- Ohne gespeicherten Background-State startet der Dienst mit gedimmtem Weiss als Grundlicht
- Logging liegt in `logs/led_controller.log`
- Release 1 ist bewusst auf den lokalen Unterprozessbetrieb ausgelegt, nicht auf einen installierten Windows-Dienst