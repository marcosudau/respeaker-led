# Dokumentation

Diese Doku ist jetzt bewusst in zwei Bereiche getrennt:

- **User-Doku**: fuer Menschen, die einfach LEDs steuern oder eigene Anzeigen bauen wollen
- **Dev-Doku**: fuer Architektur, interne Modelle und Erweiterungen am Code

## Hier anfangen

Wenn du einfach nur etwas sichtbar machen willst:

- [Hier anfangen](getting_started.md)
- [LEDs in 2 Minuten anzeigen](effects_engine_2_minuten.md)

Wenn du eigene Anzeigen bauen willst:

- [Eigene Anzeigen Schritt fuer Schritt](effects_engine_tutorial.md)
- [Welche Anzeigen es gibt](effects_engine.md)
- [Farben, Typen und Namen zum Nachschlagen](reference.md)

Wenn du erst verstehen willst, wo was im Repo liegt:

- [Wegweiser durchs Repo](layers.md)

Wenn du einen laufenden Controller von aussen steuern willst:

- [CLI und API](api_guide.md)

Wenn etwas nicht funktioniert:

- [Troubleshooting](troubleshooting.md)

## Optional und spaeter

Diese Themen brauchst du am Anfang meistens nicht:

- [Optionale Preset-Packs](presets.md)
- [Entwickler-Doku](dev/index.md)

## Wichtigster Unterschied im ganzen Repo

- **JSON/YAML-Dateien** definieren lokale Effekte und werden in Python geladen
- **CLI/API** steuern einen laufenden Controller-Prozess
- JSON/YAML werden **nicht** an die API geschickt
