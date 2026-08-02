# LED Effect Studio

Das LED Effect Studio ist der visuelle V2-Browser fuer die installierten
States, Overlays, Events und Presets. Die Eingabefelder werden zur Laufzeit
aus dem Parameterschema des ausgewaehlten Effekts erzeugt.

## Start mit ReSpeaker

Im Projektroot:

```powershell
tools\PySide6TestApp\start_effect_studio.cmd
```

Der Starter verwendet zuerst eine lokale `.venv`, danach die gemeinsame
`.venv` im uebergeordneten Experimentordner und zuletzt `python` aus `PATH`.
Das Studio startet den aktuellen Projektstand ueber `main.py` und beendet
seinen Service beim Schliessen wieder.

Nur ein laufender Controller darf gleichzeitig auf den ReSpeaker zugreifen.
Das Studio prueft deshalb die bekannten API-Ports und verweigert einen zweiten
Hardware-Service, solange bereits ein anderer Device-Controller laeuft.
Mehrere Studios koennen parallel nur mit `--no-device` verwendet werden.

## Start ohne Hardware

```powershell
tools\PySide6TestApp\start_effect_studio.cmd --no-device
```

Der Controller verwendet dann die Konsolenvorschau. Der Effektbrowser und
alle V2-Aufrufe funktionieren unveraendert.

## Wichtige Optionen

| Option | Bedeutung |
|---|---|
| `--use-device` | echte ReSpeaker-Ausgabe; Standard |
| `--no-device` | ohne USB-Hardware starten |
| `--fps <wert>` | Framerate des gestarteten Services; Standard `8` |
| `--port <port>` | bevorzugter API-Port; Standard `8765` |
| `--port-pool <liste>` | alternative Ports, beispielsweise `8766,8767` |
| `--service-exe <pfad>` | statt `main.py` eine gebaute Release-EXE testen |

Beispiel:

```powershell
tools\PySide6TestApp\start_effect_studio.cmd --fps 30 --port 8770
```

## Bedienumfang

- Suche ueber ID, Titel, Beschreibung und Quelle
- Filter fuer States, Overlays und Events
- Filter nach geladener Paketquelle oder optionaler lokaler Setauswahl
- dynamische Regler und Eingaben aus dem V2-Schema
- Farbauswahl sowie direkte Eingabe von Farbnamen oder Hexwerten
- Presets als Ausgangspunkt fuer weitere Anpassungen
- optionale Live-Aktualisierung fuer States und Overlays
- gezieltes Leeren des aktiven State- oder Studio-Overlay-Layers
- Neuladen der Effektquellen ohne Neustart des Studios
- aktuelle Parameter mit eigener Bezeichnung und Kommentar als JSON kopieren
  oder in eine Datei exportieren

Events werden nie automatisch durch die Live-Aktualisierung wiederholt.

Der Bereich `Parameterentwurf festhalten` exportiert ein bewusst einfaches
Zwischenformat. Es enthaelt Effektidentitaet, alle aktuell eingestellten
Parameter, eine frei waehlbare Bezeichnung und einen Kommentar zum gedachten
Einsatz. Diese Entwuerfe koennen bei einer spaeteren Preset-Kuration direkt
zugeordnet werden.
