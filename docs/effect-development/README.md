# Einstieg in die LEFX-V2-Entwicklung

Diese Seiten fuehren vom leeren Scaffold bis zu einem validierten `.lefx` und
einem aus mehreren Paketen gebauten `.lefxset`. Die Beispiele sind
Lernmaterial. Sie werden nicht mit den produktiven Standardeffekten
ausgeliefert.

## Zuerst den richtigen Typ waehlen

| Frage | Typ | Lebensdauer | Veraenderliche Eingaben |
|---|---|---|---|
| Soll die Anzeige als Grundzustand laufen? | State | bis zum Ersetzen oder Loeschen | keine |
| Soll eine Anwendung Daten laufend senden? | kontrolliertes Push-Overlay | bis zum Loeschen des Channels | Push-Inputs |
| Soll das Paket Werte selbst abfragen? | kontrolliertes Pull-Overlay | bis zum Loeschen des Channels | `sample_inputs()` |
| Soll eine Einblendung nach fester Zeit verschwinden? | zeitgesteuertes Overlay | endlich | keine |
| Soll ein einmaliges Signal priorisiert abgespielt werden? | Event | endlich, in der Event-Queue | keine |

Ein Effektpaket darf genau eine Definition enthalten. Presets konfigurieren
diese Definition, aendern aber niemals Typ, Overlay-Modus oder Lebensdauer.

## Empfohlener Einstieg

1. Mit `init-effect` ein gueltiges Grundgeruest erzeugen.
2. Das passende [Template](templates/README.md) als Vertragsreferenz verwenden.
3. Eines der Tutorials durcharbeiten:
   - [rotierender State](tutorials/state_rotation.md)
   - [DoA-Push-Overlay](tutorials/overlay_doa.md)
   - [kurzes Puls-Event](tutorials/event_short_pulse.md)
4. Kleine Renderbausteine in den [Snippets](snippets/effect_snippets.md) suchen.
5. Quelle validieren, als LEFX bauen und verifizieren.
6. Fuer mehrere Pakete den [LEFXSET-Build](tutorials/build_packages.md) verwenden.

```powershell
python .\tools\effect_packager.py init-effect .\my_effect `
  --effect-id my_effect --source-id my-effects --type state
python .\tools\effect_packager.py validate-effect-source .\my_effect
```

## Paket und Runtime

Eine Quelle besteht normalerweise aus:

- `effect.yaml`: Paket-ID, Source-ID und Einstiegsklasse
- `effect.py`: vollstaendige Definition und Renderlogik
- `presets.yaml`: optionale Konfigurationen derselben Definition
- optionalen lokalen Assets oder Modulen

`config` wird beim Aktivieren aufgeloest und validiert. `inputs` sind mutable
Runtime-Werte und nur bei kontrollierten Overlays erlaubt. Die Engine kennt
den Typvertrag, interpretiert aber nicht die fachliche Bedeutung eines
konkreten Effekts.

V2 besitzt keine `start`, `update`, `stop`, `reset` oder `finished` Hooks.
Animationen werden in `render()` aus der aktuellen Zeit und der Startzeit der
Instanz berechnet. Endliche Overlays und Events entfernt die Engine nach der
validierten Dauer.

## Autarkie

Jede LEFX-Quelle enthaelt ihre gesamte fachliche Renderlogik. Sie importiert
weder andere Effektpakete noch Controller-Services und besitzt keine
generische `common.py`. Die Snippets sind Kopiervorlagen, keine neue gemeinsame
Runtime-Bibliothek.

## Vertiefung

- [LEFX-Schema V2](../effect-system/05_schema_v2.md)
- [Effektuebersicht](../effects.md)
- [Buildprozess](../../tools/effect_building/BUILD_PROCESS.md)
- [CLI und HTTP API](../api_guide.md)
- [V3-Idee: optionale Lifecycle-Hooks](../planning/v3/lifecycle_hooks.md)
