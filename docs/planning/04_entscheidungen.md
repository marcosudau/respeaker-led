# Entscheidungen

Diese Datei haelt die bisher festgezogenen Architekturentscheidungen kompakt fest.

## Grundmodell

- `EffectDefinition` und `EffectInvocation` bleiben getrennt.
- Die Engine zieht das Rendering; es gibt keine eigenen Effekt-Threads als Zielmodell.
- Effektdefinition und Effektlogik sollen logisch an derselben Python-Effektklasse zusammenhaengen.
- Die Engine darf intern weiterhin getrennte Konzepte fuer Definition, Invocation und Registry verwenden.

## Layer

- Finale Layernamen:
  - `BACKGROUND_STATE_LAYER`
  - `STATE_LAYER`
  - `MAIN_LAYER`
  - `TEMP_OVERLAY_LAYER`
  - `ONGOING_OVERLAY_LAYER`
  - `EVENT_LAYER`
- `MAIN_LAYER` darf sowohl endliche als auch unendliche Effekte aufnehmen.
- Nur `EVENT_LAYER` besitzt eine Queue.

## Parameter und Dauer

- Dauer wird ueberall in `ms` standardisiert.
- `transparent` bleibt ein normaler Invocation-Parameter.
- Parameter sollen typisiert und validiert sein.
- `priority` wird von Beginn an als allgemeiner Invocation-Parameter vorgesehen.
- Default-Prioritaet einer Invocation ist der Standardwert des Ziel-Layers.

## Persistenz

- Vorerst ist nur `BACKGROUND_STATE_LAYER` persistent.
- Wenn keine gueltige Persistenz wiederhergestellt werden kann, erfolgt ein Start-Fallback auf `solid_color` in Weiss mit `brightness=0.2`.

## Event-Policy

- `EVENT_LAYER` arbeitet mit `priority + FIFO`.
- Prioritaetswerte gelten layer-uebergreifend auf einer gemeinsamen Skala.
- Kurzfristig wirkt sich das praktisch vor allem im `EVENT_LAYER` auf die Warteschlange aus.
- Laufende Events sollen standardmaessig **nicht** unterbrochen werden.
- Das Feld `preemptible` wird trotzdem vorgesehen, aber mit Default `false` fuer Events.
- Hoehere Prioritaeten beeinflussen im `EVENT_LAYER` zunaechst die Einsortierung in die Queue, nicht die Unterbrechung eines bereits laufenden Events.
- Die Dauer eines Event-Effekts beginnt erst dann, wenn das Event aktiv auf `EVENT_LAYER` laeuft; Queue-Wartezeit verbraucht keine Laufzeit.

## Einordnung in die Event-Queue

Regel:

- zuerst nach Prioritaet
- bei gleicher Prioritaet nach FIFO
- ein bereits laufendes Event bleibt standardmaessig unangetastet

Beispiel:

- Queue: `600, 600, 600, 600`
- neues Event: `601`
- Ergebnis: direkt hinter dem laufenden Event, vor allen `600er`-Events

Beispiel:

- Queue: `602, 601, 600, 600, 600`
- neues Event: `601`
- Ergebnis: hinter dem vorhandenen `601er`, vor allen `600er`-Events

## Sonderfaelle

- `direction`, `countdown`, `progress` und aehnliche Dinge sollen normale Effekte sein.
- Besonderheiten in ihrer Logik sollen im Python-Teil des Effekts leben, nicht als Runtime-Sonderpfad.

## Registry- und Discovery-Richtung

- Built-in-Discovery aus einem festen Standardpfad
- zusaetzliche Bibliothekspfade sollen explizit hinzufuegbar sein
- Refresh / Reload zur Laufzeit soll moeglich sein
- Effektlogik lebt in Python, nicht als Python-Code in JSON/YAML
- Registry-Einheit ist standardmaessig eine Python-Effektklasse mit eigener `EffectDefinition`
