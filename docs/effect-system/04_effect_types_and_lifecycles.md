# Typen und Lebenszyklen

V2 besitzt drei fachliche Definitionstypen. Overlays treten in zwei
Lebenszyklusformen auf.

## Vergleich

| Form | Lebensdauer | Aktualisierbar | Runtime-Eingaben | Channel | Queue |
|---|---|---|---|---|---|
| State | unbestimmt | durch Ersetzen | nein | nein | nein |
| Controlled Overlay | bis `clear` | ja | ja | erforderlich | nein |
| Timed Overlay | endlich | nein | nein | nein | nein |
| Event | endlich | nein | nein | nein | Prioritaets-FIFO |

## Entscheidungshilfe

| Frage | Form |
|---|---|
| Ist es ein unbestimmter visueller Grundmodus? | State |
| Besitzt eine externe Quelle veraenderliche Laufzeitdaten? | Controlled Overlay |
| Stehen Start und Ende beim Aktivieren fest? | Timed Overlay |
| Ist es ein kurzes priorisiertes Signal? | Event |

Die sichtbare Form allein reicht nicht zur Einordnung. Ein Countdown-Ring
kann Timed Overlay sein, wenn die Dauer lokal feststeht, oder Controlled
Overlay, wenn eine externe Anwendung die Restzeit verwaltet.

## State

Ein State beschreibt einen dauerhaft laufenden visuellen Grundzustand.

- Er laeuft, bis er ersetzt oder entfernt wird.
- Er besitzt keine endliche Dauer.
- Er erhaelt keine mutablen Runtime-Eingaben.
- Er darf auf Background oder Primary State eingesetzt werden, sofern seine
  Definition den jeweiligen Platz erlaubt.
- Zeitbasierte Animation wird aus `ctx.now` und der Startzeit berechnet.

Background und Primary State sind getrennte Plaetze. Sie koennen
unterschiedliche Aufgaben haben, bleiben aber beide States.

Nur der Background State kann nach seiner `LayerRule` persistiert und beim
Service-Start wiederhergestellt werden. Der Primary State ist ein laufender
Anwendungszustand und wird nicht als dauerhafte Servicekonfiguration
gespeichert.

## Controlled Overlay

Ein kontrolliertes Overlay zeigt zusaetzliche, veraenderliche Information.

- Es wird mit einem eindeutigen Channel aktiviert.
- Es laeuft unbestimmt, bis der Channel entfernt wird.
- Seine Konfiguration bleibt stabil.
- Seine Runtime-Eingaben koennen aktualisiert werden.
- Es darf transparent ueber States rendern.

DoA, Lautstaerke oder ein extern verwalteter Fortschritt sind typische
Beispiele.

Push und Pull sind lediglich Bezugsmodi seiner Runtime-Eingaben:

- `push`: Eine Integration sendet Werte an den Channel.
- `pull`: Die Engine ruft nach Policy `sample_inputs()` auf.

In beiden Faellen erzeugt `render()` den Frame.

Der Channel wird beim Setzen normalisiert und danach fuer `update` und
`clear` verwendet. Konfigurationswerte bleiben stabil; `update` akzeptiert
ausschliesslich Felder aus `runtime_input_schema`.

## Timed Overlay

Ein zeitgesteuertes Overlay ist eine endliche Einblendung ueber einem State.

- Es wird einmal mit vollstaendiger Konfiguration aktiviert.
- Es besitzt `duration_ms` oder `total_ms`.
- Es hat keinen Channel und keine mutablen Runtime-Eingaben.
- Die Engine entfernt es nach Ablauf automatisch.

Ein lokal ablaufender Countdown kann als Timed Overlay modelliert werden,
wenn Startwert und Dauer beim Aktivieren feststehen. Verwaltet eine externe
Anwendung die Restzeit, ist ein Controlled Overlay passender.

Timed Overlays akzeptieren nur die Aktivierungsaktion `on`. Sie koennen nicht
ueber einen Channel aktualisiert werden.

## Event

Ein Event beschreibt ein einmaliges, priorisiertes Signal:

- Es ist immer endlich.
- Es wird mit `emit event` ausgeloest.
- Es kann nach Aktivierung nicht aktualisiert werden.
- Es liegt in der Event-Queue.
- Die Engine beendet die aktive Instanz anhand ihrer Dauer.
- Danach aktiviert sie das naechste Queue-Element.

Warnblitz, Bestaetigungsimpuls und Benachrichtigung sind typische Beispiele.

Das bereits aktive Event wird in V2 nicht von einem neu eintreffenden Event
unterbrochen. Hoehere Prioritaet wirkt auf die wartende Queue. Das
Capability-Feld `preemptible` ist vorhanden, aktiviert aber keine allgemeine
Preemption.

## Lebenszyklusverlaeufe

```text
State:
set -> aktiv -----------------------> replace oder clear

Controlled Overlay:
set(channel) -> update/heartbeat --> update --> clear(channel)

Timed Overlay:
set -> rendern -> Dauer erreicht -> automatische Entfernung

Event:
emit -> Queue -> aktiv -> Dauer erreicht -> naechstes Event
```

## Typische Einordnungen

| Beispiel | Form | Hinweis |
|---|---|---|
| bereit, wartet, verarbeitet | State | bleibt bis zum Zustandswechsel |
| verbunden, offline, stumm | State | dauerhafte fachliche Lage |
| DoA-Richtung | Controlled Overlay | Winkel wird wiederholt geliefert |
| Lautstaerke | Controlled Overlay | externer Wert |
| Downloadfortschritt | Controlled Overlay | Anwendung besitzt den Fortschritt |
| lokal gestarteter Timer | Timed Overlay | Dauer beim Start bekannt |
| kurze Bedienanzeige | Timed Overlay | endet automatisch |
| Erfolg, Warnung, Fehlerimpuls | Event | kurzes priorisiertes Signal |

Ein dauerhaft sichtbarer Fehlerzustand ist ein State; ein kurzer Fehlerblitz
ist ein Event. Die fachliche Bezeichnung entscheidet nicht ueber den Typ.

## Verbindliche und fachliche Regeln

Der Typvertrag ist technisch verbindlich. Typische Einsatzzwecke sind
Orientierung, keine zusaetzliche hartkodierte Anwendungslogik. Die Engine
weiss, dass ein Event endlich ist. Sie weiss nicht, ob es eine Warnung oder
eine Bestaetigung darstellt.

Ungueltig sind insbesondere:

- State mit Runtime-Eingaben,
- Controlled Overlay ohne unbestimmten Lebenszyklus,
- Timed Overlay ohne endliche Dauer,
- Event mit Channel oder Update,
- Preset, das den Typ oder Overlay-Modus veraendert.
