# Status und Ausblick

Diese Seite trennt den implementierten Ist-Zustand von noch offenen Arbeiten
und unverbindlichen Zukunftsideen.

## Statusbegriffe

| Status | Bedeutung |
|---|---|
| Implementiert | Bestandteil des aktuellen V2-Systems |
| Verifiziert | durch automatisierte oder praktische Pruefung bestaetigt |
| Offen | geplante Arbeit innerhalb der aktuellen Ausbaustufe |
| V3-Idee | nicht beschlossen und nicht Bestandteil von V2 |

## Implementiert

- strikte State-, Overlay- und Event-Vertraege
- Controlled und Timed Overlay
- getrennte Konfiguration und Runtime-Eingaben
- Push/Pull-Sampling mit Input-Health
- kanonische Wertnormalisierung und deutsche/englische Farbaliasse
- verb-zentrierte CLI und HTTP API
- kompakte Listen und getrennte Detailabfragen
- Build, Laden und Verifikation von `lefx/2` und `lefxset/2`
- autarke First-Party-Quellen ausserhalb von `build/`
- Entfernung der zentralen effektbezogenen Normalisierungslogik
- Paketgrenzen ohne `common.py` und Controller-Imports

## Verifiziert

- Quellen-, Schema-, Import- und Paketvalidierung
- Render-Smoke-Tests fuer First-Party-Definitionen
- Einzel-LEFX- und Standard-LEFXSET-Build
- State-, Overlay-, Event-, API-, CLI- und Runtime-Verhalten durch
  automatisierte Tests
- validierbare Templates und Tutorial-Pakete ausserhalb des Produktkatalogs

Die konkrete Testanzahl wird hier nicht festgeschrieben, weil sie sich mit der
Weiterentwicklung aendert.

## DoA

Die ReSpeaker-Hardware besitzt die Firmware, die DoA-Werte vom internen
LED-Effekt entkoppelt. Damit ist die technische Voraussetzung erfuellt.

Die produktive End-to-End-Integration ist umgesetzt: Der Controller liest
`DOA_VALUE` zentral mit maximal 30 Hz, cached Winkel und VAD und stellt den
Snapshot ueber `respeaker_doa` bereit. Der transparente
`direction_indicator` enthaelt nur die Darstellung einer einzelnen
Richtungs-LED. Weitere DoA-Auswertungen auf Basis von Azimut- und
Beam-Energiewerten bleiben bewusst Gegenstand spaeterer Experimente.

## Produktiver Effektkatalog

Die migrierten First-Party-Definitionen sind technisch V2-faehig. Vor der
gemeinsamen Integration in den Hauptstand werden sie noch:

- einzeln qualitativ ueberarbeitet,
- visuell abgestimmt,
- sinnvoll benannt,
- thematisch in hochwertige LEFXSETs gruppiert,
- auf redundante oder schwache Varianten geprueft.

Die Tutorial-Beispiele sind Lernmaterial und werden nicht als produktive
Definitionen ausgeliefert.

## Kompatibilitaetsgrenzen

LEFX V1 wird nicht still geraten oder automatisch konvertiert. Eine spaetere
Migration benoetigt eine ausdrueckliche, pruefbare Strategie.

Verbleibende anwendungsspezifische Kompatibilitaetsflaechen werden getrennt
bewertet. Sie duerfen die V2-Paket- und Enginegrenzen nicht aufweichen.

## Bekannte Grenzen des aktuellen V2-Standes

- Der Controller ist aktuell auf einen zwoelfteiligen ReSpeaker-Ring
  ausgelegt.
- Der Controlled-Overlay-Layer traegt eine aktive kontrollierte Instanz
  gleichzeitig; Channels erzeugen keine zusaetzlichen Layer.
- Zur Laufzeit registrierte Paketquellen werden nicht als dauerhafte
  Benutzerkonfiguration persistiert.
- `min_service_version` und optionale Hardwaremetadaten werden im Manifest
  transportiert, aber noch nicht gegen eine Versions- oder Hardwarepolicy
  erzwungen.
- Mehrere Capability-Felder beschreiben den Vertrag, besitzen aber noch keine
  allgemeine Runtime-Policy. Insbesondere unterbricht `preemptible` kein
  laufendes Event.
- LEFX-Pakete werden per SHA-256 auf Integritaet geprueft, sind aber nicht
  signiert und laufen nicht in einer Sandbox.
- V1-Betriebs-, Quellen- und Anwendungskompatibilitaetsrouten sind weiterhin
  vorhanden.

Diese Punkte sind dokumentierte Grenzen, keine stillen Erweiterungszusagen.

## Noch offene V2-Arbeiten

| Bereich | Offener Schritt |
|---|---|
| First-Party-Katalog | visuelle Qualitaetspruefung und Bereinigung |
| LEFXSETs | thematische, produktive Zusammenstellung |
| DoA | echter USB-Datenstrom bis zum V2-Push-Channel |
| Paketbetrieb | spaetere Entscheidung zu Persistenz externer Quellen |
| Kompatibilitaet | V1-Routen einzeln bewerten und migrieren |
| Security | Vertrauens- und Signaturmodell nur bei Bedarf gesondert planen |

## V3-Ideen

Optionale Lifecycle-Hooks fuer echten paketlokalen Zustand sind lediglich
eine Ideensammlung. V2 bleibt renderorientiert und engine-gesteuert.

Aktive Zukunftsplanung liegt unter `docs/planning/`. Historische Konzepte,
Sanierungsberichte und abgeloeste Zwischenstaende liegen unter
`docs/archive/` und sind nicht normativ.
