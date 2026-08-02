# Architekturgrenzen

Autarke Pakete und eine generische Engine funktionieren nur, wenn
Verantwortungen verbindlich getrennt bleiben.

## Verantwortungsmatrix

| Bereich | Besitzt |
|---|---|
| LEFX-Paket | visuelle Bedeutung, Schemas, Renderlogik, lokale Assets und optionale Presets |
| Engine | Typvertraege, Lebenszyklen, Layer, Komposition, Queue, Input-Health und Hardwareausgabe |
| Integration | Hardwarezugriff, externe Datenquellen und anwendungsspezifische Zuordnung |
| CLI/API | Transport, Validierungsfehler und Darstellung der Ergebnisse |
| Build | Quellenpruefung, Paketierung und Verifikation |

## Paketautarkie

Eine LEFX-Quelle enthaelt alle Logik, die ihre konkrete Darstellung benoetigt.
Erlaubt sind:

- `effect.py`,
- paketlokale Hilfsmodule mit fachlich konkretem Namen,
- paketlokale Assets,
- versionierte, ausdruecklich erlaubte SDK- und Standardbibliotheksimporte.

Nicht erlaubt sind:

- generische `common.py`,
- gemeinsam genutzte Effektimplementierungen,
- Importe anderer LEFX-Pakete,
- Controller-, Service- oder Registry-Zugriffe.

### Korrekt

```text
doa_marker/
|-- effect.py
|-- geometry.py
`-- effect.yaml
```

`geometry.py` gehoert nur zu dieser Definition und wird mit dem Paket
ausgeliefert.

### Falsch

```text
effects/common.py
states/a.py -> import common
overlays/b.py -> import common
```

Damit waeren Pakete nicht mehr unabhaengig baubar oder installierbar.

### Gemeinsamer SDK-Code

Paketautarkie verbietet nicht den stabilen Vertrag, den Engine und Pakete
gemeinsam benoetigen. Erlaubt sind ausschliesslich die freigegebenen
SDK-Module:

- `src.core.effect_schema`
- `src.core.color_math`

Sie stellen Datentypen und generische Farbmathematik bereit. Konkrete
Geometrie, Animationen, Defaults oder fachliche Zuordnungen duerfen dort
nicht gesammelt werden.

## Generische Engine

Die Engine darf nach Typ, Overlay-Modus, Layer-Regel und Capability
entscheiden. Sie darf nicht anhand einer konkreten ID verzweigen.

### Korrekt

```python
if definition.definition_type is DefinitionType.EVENT:
    enqueue(invocation)
```

### Falsch

```python
if definition.id == "warning_flash":
    enqueue(invocation)
```

Die Bedeutung `warning` gehoert ins Paket oder in eine Integration.

## Integrationen

Integrationen verbinden externe Systeme mit den generischen
Steuerungskommandos. Dazu gehoeren:

- ReSpeaker-USB-Zugriff,
- Wiederverbindung und Geraeteauswahl,
- Anwendungsereignisse,
- Zuordnung fachlicher Signale zu Definition und Channel.

Ein DoA-Paket rendert `direction_deg`. Es oeffnet nicht selbst das
USB-Geraet.

Anwendungsintegrationen duerfen stabile Definition- oder Preset-IDs
referenzieren, weil sie die fachliche Zuordnung besitzen. Die generische
Engine darf diese Zuordnung nicht kennen.

## Pull-Grenze

`sample_inputs()` ist ein von der Engine kontrollierter Einstieg fuer
begrenzte paketlokale Datenquellen. Es ist keine zweite Controller-Runtime.

- kein unverwalteter Hintergrundthread,
- kein blockierendes I/O in `render()`,
- Sampling nur nach der deklarierten Policy,
- Fehler werden ueber Input-Health sichtbar,
- gemeinsam genutzte Hardware bleibt Aufgabe einer Integration.

Bei gemeinsam genutzten Hardwarewerten besitzt der Controller den
Polling-Takt und den Cache. Ein Paket deklariert nur die `provider_id` und
liest den validierten Snapshot. Effektanzahl und USB-Abfragerate sind dadurch
voneinander entkoppelt.

## Rendergrenze

`render()` soll fuer einen gegebenen Kontext deterministisch und schnell einen
Frame liefern. Zeitbasierte Animation verwendet absolute Zeitdifferenzen:

```python
elapsed = ctx.now - ctx.invocation.created_at
```

Das Paket besitzt keinen eigenen Start-, Stop-, Reset- oder Finished-Hook in
V2. Es beendet keine Engine-Instanz selbst.

Eine Paketklasse kann fuer ihre laufende Invocation internen Python-Zustand
halten, weil der Composer eine Instanz pro Invocation verwaltet. Ohne
Lifecycle-Hooks darf dieser Zustand aber nicht fuer externe Ressourcen,
Threads oder notwendige Abschlussarbeit verwendet werden.

## Normalisierung

Generische Normalisierung von Farbe, Dauer, Bool, Winkel oder Prozentwert
gehoert an die Systemgrenze. Konkrete Bedeutung bleibt lokal:

```text
Generisch: "blau" -> "#0000FF"
Paketlokal: direction_deg -> Position auf dem Ring
Integration: Mikrofonwert -> DoA-Channel
```

Eine zentrale Datei darf deshalb keine Defaults oder Verhaltenszweige fuer
konkrete Definitionen enthalten.

## Vertrauensgrenze

LEFX ist ein Paketformat fuer ausfuehrbaren Python-Code, kein
Sandboxformat. Hashes pruefen Integritaet, aber nicht Herkunft oder
Unbedenklichkeit.

Verbindliche Betriebsregel:

- nur vertrauenswuerdige Pakete laden,
- Fremdpakete vor der Registrierung pruefen,
- keine Geheimnisse oder unkontrollierten Hardwarezugriffe im Paket,
- Signatur- oder Trust-Store-Angaben nicht vortaeuschen; sie sind in V2 nicht
  implementiert.

## Modulzuordnung

| Fragestellung | Zustaendiger Bereich |
|---|---|
| Welche Werte darf die Definition annehmen? | LEFX-Schema im Paket |
| Wie wird ein Wert in Pixel uebersetzt? | Paket-Renderlogik |
| Wann startet oder endet eine Instanz? | Runtime |
| Welcher Layer liegt oben? | LayerStore und Renderer |
| Woher kommt ein USB- oder App-Wert? | Integration |
| Wie wird `blau` normalisiert? | generische Wertnormalisierung |
| Wie wird eine ID gefunden? | Registry |
| Wie wird ein Paket geprueft? | Builder und Loader |
| Wie wird ein Request transportiert? | CLI, Client oder API |

## Prueffragen fuer neue Logik

1. Ist die Regel fuer alle Definitionen dieses Typs gueltig? Dann kann sie in
   die Engine gehoeren.
2. Beschreibt sie die konkrete Darstellung? Dann gehoert sie ins LEFX-Paket.
3. Beschafft oder uebersetzt sie externe Daten? Dann gehoert sie in eine
   Integration.
4. Dient sie nur Transport oder Ausgabe? Dann gehoert sie zu CLI/API.
