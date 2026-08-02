# Fahrplan fuer die Effektsystem-Dokumentation

Status: Vollstaendig umgesetzt und am 2026-07-30 archiviert.

## Ziel

Die normale Dokumentation soll den aktuellen Ist-Zustand von LEFX V2
verstaendlich und verbindlich beschreiben. Sie wird klar von praktischen
Entwicklungsanleitungen, Planungsunterlagen und historischen Dokumenten
getrennt.

## Dokumentationsebenen

```text
docs/effects.md
    Kurzer Einstieg und Verteiler fuer alle Zielgruppen

docs/effect-system/
    Verbindliche Beschreibung des aktuellen V2-Systems

docs/effect-development/
    Praktische Entwicklungshilfe, Templates und Tutorials

docs/planning/
    Aktive Planung und noch nicht umgesetzte Entscheidungen

docs/archive/
    Historische, abgeloeste oder nur noch nachvollziehbare Unterlagen
```

## Verbindliche Kapitelstruktur

1. `01_overview.md`
   Ueberblick, Grundidee und mentales Modell.
2. `02_vocabulary.md`
   Verbindliche Begriffe und Systemobjekte.
3. `03_layers_and_composition.md`
   Layer-Stapel, LED-Frames, Prioritaeten, Transparenz und Komposition.
4. `04_effect_types_and_lifecycles.md`
   State, Overlay und Event mit ihren jeweiligen Lebenszyklen.
5. `05_schema_v2.md`
   Verbindliches Datenmodell und alle Schema-Invarianten.
6. `06_parameters_and_values.md`
   Parameter, Farben, Aliase und Normalisierung.
7. `07_runtime_inputs.md`
   Push, Pull, Channels, Heartbeat und datengetriebene Overlays.
8. `08_packages_ids_and_configuration.md`
   LEFX, LEFXSET, IDs, freie Konfiguration und optionale Presets.
9. `09_control_interface.md`
   Bedienmodell fuer CLI und HTTP API.
10. `10_validation_and_build.md`
    Validierung, Smoke-Render, Build, Verifikation und Auslieferung.
11. `11_architecture_boundaries.md`
    Verantwortlichkeiten und verbindliche Architekturgrenzen.
12. `12_status_and_outlook.md`
    Umsetzungsstand, Grenzen und klar getrennte Zukunftsthemen.

`docs/effect-system/README.md` wird die zentrale Navigation fuer die
Zielgruppen Systemverstaendnis, Bedienung und Effektentwicklung.

## Redaktionsregeln

- `docs/effect-system/` beschreibt ausschliesslich implementierten Ist-Zustand.
- Jede Aussage besitzt genau eine ausfuehrliche Hauptquelle.
- Andere Seiten verlinken auf diese Quelle, statt Inhalte zu duplizieren.
- Definition, Paket, Preset und laufende Instanz werden nicht pauschal als
  dasselbe Objekt bezeichnet.
- Die beiden Overlay-Modi werden sichtbar getrennt.
- DoA dient als durchgaengiges Beispiel fuer externe Runtime-Daten.
- Rotierender State und Puls-Event dienen als einfache Lifecycle-Beispiele.
- Architekturregeln erhalten gueltige und ungueltige Gegenbeispiele.
- Nicht implementierte Ideen werden nicht mit dem Ist-Zustand vermischt.
- Historische Unterlagen bleiben auffindbar, steuern aber keine aktuelle
  Implementierung.

## Gemeinsamer Erarbeitungsprozess

Fuer jedes Kapitel wird vor dem Schreiben festgelegt:

1. Ziel und Zielgruppe.
2. Kernaussagen und Prioritaeten.
3. Begriffe und verbindliche Formulierungen.
4. Tabellen, Diagramme und Beispiele.
5. Abgrenzung zu anderen Kapiteln.
6. Zu uebernehmende oder zu archivierende Bestandsdokumente.
7. Offene Entscheidungen.

Erst nach der inhaltlichen Freigabe aller Kapitel werden die normale
Dokumentation und die Bereinigung des Dokumentationsordners umgesetzt.

## Kapitelstatus

| Kapitel | Status |
|---|---|
| 1. Ueberblick und Grundidee | Inhaltlich freigegeben |
| 2. Begriffe und Systemobjekte | Inhaltlich freigegeben |
| 3 bis 5 | Inhaltlich freigegeben |
| 6 bis 8 | Inhaltlich freigegeben |
| 9 bis 11 | Inhaltlich freigegeben |
| 12 | Inhaltlich freigegeben |

## Freigegebene Detailstruktur: Kapitel 1

Kapitel 1 beginnt mit dem heutigen Modell. Die fruehere Hartkodierung wird nur
als kurze Motivation und in einem kompakten Vorher-Nachher-Vergleich erwaehnt.

Verbindliche Abschnitte:

1. Was ist das Effektsystem?
2. Warum wurde die Logik getrennt?
3. Das mentale Grundmodell:
   `LEFX-Quelle -> LEFX-Paket -> geladene Definition -> laufende Instanz`
4. Drei fachliche Typen und vier Lebenszyklusformen.
5. Verantwortungsgrenzen zwischen LEFX-Paket, Engine, Integration und
   Steuerungsschnittstelle.
6. Vollstaendiger Datenfluss anhand von DoA und einem kurzen Event.
7. LEFX, LEFXSET und Preset jeweils in einem Satz.
8. Navigation zu den anschliessenden Vertiefungen.

Verbindliche Schwerpunktsetzung:

- Autonomie der Effektpakete steht im Vordergrund.
- Der Controller kennt Typvertraege, aber keine konkrete Effektbedeutung.
- Es gibt drei fachliche Typen; kontrollierte und zeitgesteuerte Overlays
  werden als getrennte Lebenszyklusformen sichtbar gemacht.
- Definition, Paket und laufende Instanz werden als unterschiedliche Objekte
  eingefuehrt.
- `Effektsystem` bleibt der allgemeine Oberbegriff. In technischen Aussagen
  werden die konkreten Objekte praezise benannt.
- Der ReSpeaker bleibt der konkrete Hauptanwendungsfall, waehrend die
  Architektur hardwareunabhaengig beschrieben wird.
- Controllerzugriffe aus LEFX-Paketen werden bereits ausgeschlossen.
  Threading- und weitere technische Einzelheiten folgen erst im Kapitel zu den
  Architekturgrenzen.
- Schemafelder, vollstaendige Layerregeln, Heartbeatdetails, ID-Aufloesung und
  Buildbefehle werden in Kapitel 1 bewusst noch nicht vertieft.

## Freigegebene Detailstruktur: Kapitel 2

Kapitel 2 legt die verbindliche Sprache fuer Quelle, Paket, Definition,
Konfiguration und laufende Ausfuehrung fest.

Verbindliche Abschnitte:

1. Warum feste Begriffe notwendig sind.
2. Objektkette von LEFX-Quelle ueber Paket und Definition zur laufenden
   Instanz.
3. LEFX-Quelle.
4. LEFX-Paket.
5. Definition.
6. Preset.
7. Konfiguration und Runtime-Eingaben.
8. Steuerungskommando.
9. Laufende Instanz.
10. Overlay-Channel.
11. Layer.
12. LEFXSET.
13. ID-Arten und Namensraeume als kurzer Ausblick.
14. Verbindliche Sprachregel fuer den Begriff `Effekt`.

Verbindliche Begriffsentscheidungen:

- `LEFX-Paket` ist der normale Begriff. `Artefakt` wird nur verwendet, wenn
  ausdruecklich das Ergebnis eines Builds gemeint ist.
- Nach der ersten Erklaerung von `Effektdefinition` wird `Definition` als
  Kurzform verwendet.
- Die allgemeine Dokumentation spricht von einer `laufenden Instanz`.
  Der interne Klassenname `EffectInvocation` erscheint erst in der technischen
  Referenz.
- Eine validierte, transportunabhaengige Operation heisst
  `Steuerungskommando`. Der Begriff gilt fuer CLI und HTTP API.
- Das alleinstehende Wort `Effekt` wird in technischen Aussagen moeglichst
  vermieden. `Effektsystem` und `Effektentwicklung` bleiben als eindeutige
  Oberbegriffe erlaubt.
- Alte V1-Begriffe und ihre historischen Entsprechungen werden nicht in die
  aktuelle Dokumentation aufgenommen. Eine entsprechende Uebersetzungstabelle
  gehoert ausschliesslich in den spaeteren Archivbereich.

## Freigegebene Detailstruktur: Kapitel 3 bis 5

### Kapitel 3: Layer und Komposition

Das Layer- und Kompositionsprinzip wird vor den Effekttypen erklaert, weil
deren fachliche Trennung auf ihrer Rolle im gemeinsamen LED-Bild aufbaut.

Verbindliche Inhalte:

- Begriff und Aufgabe eines LED-Frames.
- Layer-Stapel von Background State bis Event.
- Lesbare Layer-Namen mit ergaenzenden technischen Enum-Namen.
- Prioritaet und Ueberlagerung.
- Deckende und transparente Komposition.
- Bedeutung von `None` als unveraenderter Wert des darunterliegenden Frames.
- Ausfuehrliches Schaubild des Stapels und des daraus komponierten Endframes.
- Keine freie oeffentliche Layerauswahl; der Typvertrag bestimmt die
  Platzierung.
- Kontrollierte Overlays liegen im aktuellen V2-Modell ueber zeitgesteuerten
  Overlays.

### Kapitel 4: Typen und Lebenszyklen

Verbindliche Inhalte:

- Drei fachliche Typen: State, Overlay und Event.
- Kontrollierte und zeitgesteuerte Overlays als unterschiedliche
  Lebenszyklusformen.
- Zweck, Lebensdauer, Aktivierung, Aktualisierbarkeit, Beendigung,
  Runtime-Eingaben, Channel und Queue je Lebenszyklusform.
- Background und Primary als zwei unterschiedliche State-Plaetze.
- Typvertrag als verbindliche Regel; fachliche Beispiele als Orientierung.
- Neutrale Beispiele, solange der produktive Effektkatalog noch ueberarbeitet
  wird.
- Push und Pull sind keine Overlay-Untertypen. Sie sind zwei Bezugsmodi fuer
  Runtime-Eingaben und nur ein einzelner Aspekt kontrollierter Overlays.
- Push und Pull liefern keine fertigen Frames. `render()` erzeugt weiterhin
  jeden Frame aus Konfiguration, Runtime-Eingaben und Renderkontext.

### Kapitel 5: Schema V2

Verbindliche Inhalte:

- Vollstaendige deutsche Feldreferenz mit unveraenderten englischen
  Codebezeichnern.
- Kennzeichnung als `Verpflichtend`, `Bedingt`, `Optional` oder `Empfehlung`.
- Identitaet, Metadaten, Typ, Overlay-Modus, Konfigurationsschema,
  Runtime-Input-Schema, Defaults, Capabilities, Layer-Regeln, Farbmodell,
  Komposition, Animation, Richtung und Input-Sampling.
- Typbezogene Invarianten und ungueltige Kombinationen.
- Kleine kanonische Codeausschnitte; vollstaendige Quellen werden aus der
  Entwicklerdokumentation verlinkt.
- Die bestehende V2-Schemadatei wird in die aktuelle Referenz ueberfuehrt.
  Ihr bisheriger Planungsort erhaelt nur einen historischen Hinweis.

## Freigegebene Detailstruktur: Kapitel 6 bis 8

### Kapitel 6: Parameter und Werte

Verbindliche Inhalte:

- Konfigurationsaufloesung aus Defaults, optionalem Preset und expliziten
  Werten des Steuerungskommandos.
- Standardfelder werden nur bei einem passenden Merkmal verpflichtend.
- Vollstaendige Erklaerung der Farbmodelle `none`, `mono`, `dual`, `palette`,
  `gradient` und `random_range`.
- `speed` ist ein Multiplikator der entworfenen Grundgeschwindigkeit und keine
  FPS-Angabe.
- Komfortnotationen und deutsche beziehungsweise englische Aliase werden nur
  an der Systemgrenze akzeptiert.
- Interne Werte sind kanonisch und strikt.
- Zufallsfarben bleiben durch `random_seed` reproduzierbar.
- Renderer implementieren keine parallelen Eingabeparser.

### Kapitel 7: Runtime-Eingaben

Verbindliche Inhalte:

- Konfiguration und Runtime-Eingaben werden gegenuebergestellt.
- Nur kontrollierte Overlays besitzen mutable Runtime-Eingaben.
- Channel, Push, Pull, Sampling-Intervall, Heartbeat, Karenzzeit,
  Input-Health und `None` werden vollstaendig erklaert.
- Push und Pull heissen Bezugsmodi fuer Runtime-Eingaben und sind keine
  Overlay-Untertypen.
- Die Engine bewertet den Empfangszustand, nicht die fachliche Qualitaet eines
  Messwertes.
- DoA zeigt einen extern gelieferten Richtungswert.
- Eine Lautstaerkeanzeige zeigt normale Push-Aktualisierungen mit `progress`.
- Ein Countdown zeigt die Modellentscheidung:
  engine-timed bei einer festen Dauer, kontrolliert bei einem extern
  verwalteten Restwert.
- Ein neutrales, paketlokales Beispiel veranschaulicht Pull.

### Kapitel 8: Pakete, IDs und Konfiguration

Die freie Parametrisierung einer Definition steht vor den Presets und wird als
Normalfall beschrieben.

Verbindliche Inhalte:

- Quelle, gebautes LEFX-Paket und LEFXSET.
- Source-ID, Package-ID, Definition-ID, qualifizierte ID und globale
  Namensraeume.
- Kurze IDs sind die normale Benutzerform.
- Explizite Werte koennen innerhalb des Schemas frei gesetzt werden.
- Ein Preset ist lediglich ein optionaler, benannter und kuratierter
  Konfigurationsvorschlag beziehungsweise Startpunkt.
- Presets sind weder die Hauptbedienform noch eine Begrenzung der moeglichen
  Konfigurationen.
- Presets enthalten nur Konfiguration und veraendern keinen Typ oder
  Lebenszyklus.
- LEFXSETs sind kuratierte Auslieferungseinheiten ohne eigenes Verhalten.
- Die endgueltigen produktiven Set-Namen und Inhalte werden erst bei der
  anschliessenden Ueberarbeitung des Effektkatalogs festgelegt.

## Freigegebene Detailstruktur: Kapitel 9 bis 11

### Kapitel 9: Bedienung ueber CLI und API

Verbindliche Inhalte:

- `Steuerungskommando` ist das gemeinsame Modell fuer CLI und HTTP API.
- Die kanonische Verb-zuerst-Grammatik verwendet `set`, `update`, `clear`,
  `emit`, `list` und `show`.
- Dokumentiert werden nur vollstaendige kanonische Formen.
- Eindeutige Kurzformen bleiben eine undokumentierte Eingabehilfe und melden
  nach Annahme die kanonische Form.
- Ein blosses `set` bedeutet idempotent einschalten. Toggle wird nur
  ausdruecklich angefordert.
- Listen liefern standardmaessig kompakte IDs.
- Details und JSON-Ausgabe werden getrennt erklaert.
- API-Antworten bleiben immer JSON.
- Ungueltige Eingaben veraendern keine Runtime.
- Unscharfe Treffer werden nur vorgeschlagen und nie automatisch ausgefuehrt.

### Kapitel 10: Validierung und Build

Verbindliche Inhalte:

- Qualitaetskette von Quelle ueber Struktur-, Import-, Schema-,
  Vertrags- und Smoke-Render-Pruefung bis zum verifizierten LEFX-Paket.
- LEFXSETs werden bevorzugt aus bereits geprueften LEFX-Paketen gebaut.
- Autoritative Quellen liegen niemals unter `build/`.
- Standard- und Fremdpakete verwenden dieselben grundlegenden Pruefschritte.
- Smoke-Render ergaenzt Tests und ersetzt sie nicht.
- Temporaere Caches und fertige Ausgaben werden getrennt.
- Erfolgreiche Standard-Builds bereinigen ihre Zwischen-Caches.
- Eine kompakte Build-Checkliste wird aufgenommen.
- Vollstaendige Befehlsfolgen bleiben in der Entwicklerdokumentation.
- Fehler werden nach Quelle, Schema, Import, Render und Paketstruktur
  gruppiert.

### Kapitel 11: Architekturgrenzen

Verbindliche Inhalte:

- Verantwortungsmatrix fuer LEFX-Paket, Engine, Integration und
  Steuerungsschnittstelle.
- Kein Controller-Verhalten anhand konkreter Definition-IDs.
- Keine gemeinsam genutzte Effektlogik oder generische `common.py`.
- Paketlokale Hilfsmodule und Assets bleiben erlaubt.
- Keine Imports anderer LEFX-Pakete.
- Kein blockierendes I/O in `render()`.
- Keine unverwalteten Hintergrundthreads in Paketen.
- `sample_inputs()` ist der kontrollierte Pull-Einstieg und keine zweite
  Controller-Runtime.
- Hardwarezugriffe liegen grundsaetzlich in Integrationen. Pull bleibt auf
  begrenzte paketlokale Datenquellen beschraenkt.
- Allgemeine Validierung bleibt generisch; konkrete Effektbedeutung bleibt im
  Paket.
- Jede zentrale Architekturregel erhaelt mindestens ein korrektes und ein
  falsches Gegenbeispiel.

## Freigegebene Detailstruktur: Kapitel 12

### Kapitel 12: Status und Ausblick

Kapitel 12 trennt dauerhaft zwischen `Implementiert`, `Verifiziert`, `Offen`
und `V3-Idee`.

Verbindliche Inhalte:

- Umsetzungsstand von Schema, Runtime, CLI/API, Build und Paketvalidierung.
- Die ReSpeaker-Firmware mit entkoppelten DoA-Werten ist installiert.
- Die produktive Live-USB-Integration bleibt als getrennte Arbeit offen.
- Die mitgelieferten Definitionen werden noch qualitativ ueberarbeitet und
  thematisch gruppiert.
- LEFX-V1-Pakete werden nicht automatisch geraten oder still konvertiert.
- Lifecycle-Hooks bleiben eine V3-Idee.
- Ausfuehrliche Entwicklungsgeschichte wird nur im Archiv verlinkt.
- Keine volatile Aufgabenliste und keine fest eingetragene Testanzahl.

## Verbindliche Zielstruktur von `docs`

```text
docs/
|-- index.md
|-- getting_started.md
|-- api_guide.md
|-- troubleshooting.md
|-- effects.md
|-- effect-system/
|   |-- README.md
|   `-- 01 bis 12
|-- effect-development/
|   |-- templates/
|   |-- tutorials/
|   `-- snippets/
|-- examples/
|   `-- effects/
|-- dev/
|   |-- index.md
|   |-- architecture.md
|   |-- build.md
|   `-- public_entry_points.md
|-- planning/
|   |-- index.md
|   `-- v3/
`-- archive/
    |-- README.md
    |-- project-history/
    |-- effect-concepts/
    |-- sanitation-reports/
    `-- prompts/
```

Verbindliche Zuordnung:

- `effects.md` bleibt ein kurzer Verteiler.
- `current_approach.md` wird in aktuelle Architekturkapitel eingearbeitet.
- `presets.md` geht in Kapitel 8 auf.
- `lefx_schema_v2.md` geht in Kapitel 5 auf.
- Bisherige Reports werden unter `archive/sanitation-reports/` archiviert.
- `history_and_legacy` wird unter `archive/project-history/` archiviert.
- Alte Effektkonzepte und Konzeptreihen werden unter
  `archive/effect-concepts/` archiviert.
- Abgearbeitete Prompts werden unter `archive/prompts/` archiviert.
- V3-Ideen liegen unter `planning/v3/`, nicht in der aktuellen
  Entwicklerdokumentation.
- `planning/` enthaelt danach nur tatsaechlich offene Planung.

## Bereinigungsprinzip fuer `docs`

Jede vorhandene Datei wird einer der folgenden Rollen zugeordnet:

- aktuelle Nutzer- oder Systemdokumentation
- aktuelle Entwicklerdokumentation
- aktive Planung
- historisches Archiv
- Duplikat oder ersetzbarer Zwischenstand

Alle alten Dokumentationsdateien werden archiviert. Es wird keine historische
Datei geloescht, auch wenn sie leer, doppelt, abgeloest oder nur ein
Zwischenstand ist. Solche Dateien werden im Archiv sichtbar als leer,
redundant oder abgeloest gekennzeichnet.

Die Migration erhaelt eine Tabelle mit altem Pfad, neuem Archivpfad,
Dokumentrolle und gegebenenfalls der aktuellen Nachfolgedokumentation.
Historische Dateien werden nicht stillschweigend als aktuelle Referenz
weitergefuehrt. Jeder Archivbereich erhaelt eine README, die seinen
nicht-normativen Status erklaert.

Nur fuer nachweislich relevante alte Einstiegspfade bleiben kleine
Verweisdateien bestehen. Alle internen Links werden auf die neue Struktur
umgestellt und automatisiert geprueft.
