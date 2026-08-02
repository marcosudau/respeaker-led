# Konzept: Effekt-Dateien und Effekt-Set-Dateien

Stand: 2026-04-10
Status: hypothetisches Architekturkonzept, keine Implementierung

## Ausgangsidee

Die Anwendung soll nicht mehr zwingend rohe Effektparameter an den laufenden Service schicken muessen.

Stattdessen soll sie eigene, fertig vorbereitete Effekt-Artefakte mitbringen koennen:

- ein Artefakt fuer genau einen konkreten Effekt
- optional ein Container-Artefakt fuer mehrere konkrete Effekte als Set

Diese Artefakte sollen:

- moeglichst eigenstaendig sein
- alle benoetigten Informationen fuer Registrierung und Ausfuehrung enthalten
- die Anwendungslogik vereinfachen
- den eigentlichen Effekt fuer die Anwendung als fertigen Befehl oder Namen kapseln
- nach dem Bauen nicht mehr ohne Weiteres lesbar oder veraenderbar sein

## Einordnung der Idee

Die Richtung ist sinnvoll.

Der groesste praktische Gewinn waere nicht primär in der Render-Engine selbst, sondern in der Distributions- und Integrationsschicht:

- Anwendungen koennen ihren Effektbestand als fertiges Paket mitbringen.
- Die Anwendung muss weniger ueber `effect_id`, Parameter, Layerregeln und Defaults wissen.
- Die Kopplung zwischen Anwendung und Service sinkt, weil die Anwendung nicht mehr viel Effektwissen eingebaut haben muss.
- Der Service bekommt eine klarere Erweiterungsschnittstelle fuer fremde oder projektspezifische Effektbibliotheken.

Die Idee hat aber nur dann eine saubere Architektur, wenn man strikt zwischen drei Ebenen trennt:

1. Laufzeitmodell
2. Quellformat
3. Distributionsformat

Wenn man diese Ebenen vermischt, wird das System schnell schwer wartbar.

## Die drei Ebenen, die man trennen sollte

### 1. Laufzeitmodell

Das ist das, was der Service intern wirklich braucht.

Heute sind das sinngemaess:

- `BaseEffect`
- `EffectDefinition`
- `render(ctx)`
- Registry-Eintrag
- Invocation gegen einen Layer

Diese Ebene sollte stabil bleiben.

Der Service sollte intern weiterhin immer auf eine normale registrierte Effektklasse oder ein normalisiertes Effektobjekt hinauslaufen.

### 2. Quellformat

Das ist das Format, in dem ein Effekt entwickelt oder beschrieben wird.

Beispiele:

- Python-Modul
- YAML/JSON-Manifest plus Python-Renderer
- DSL plus Assets plus Metadaten

Das Quellformat ist fuer Entwickler gedacht.

Es darf lesbar und editierbar sein.

### 3. Distributionsformat

Das ist das, was an Anwendungen oder Deployments verteilt wird.

Beispiele:

- einzelne gepackte Effekt-Datei
- gepacktes Effekt-Set
- signiertes Bundle

Das Distributionsformat ist fuer Installation, Registrierung und Auslieferung gedacht.

Wenn du willst, dass der Inhalt spaeter nicht mehr lesbar oder veraenderbar ist, dann gehoert diese Forderung genau hierhin, nicht in das Laufzeitmodell.

## Mein Kernurteil

Die Idee ist gut, aber ich wuerde sie nicht als neuen nativen Effekt-Typ der Engine bauen.

Ich wuerde sie als verpackte Erweiterungsartefakte ueber der bestehenden Effektbibliothek bauen.

Das bedeutet:

- Die Runtime bleibt einfach.
- Die Registry bekommt zusaetzliche Loader.
- Es kommt ein Packaging-Format dazu.
- Anwendungen liefern fertige Effektpakete mit.
- Der Service kann diese Pakete registrieren.

Das ist effizienter als eine komplette Neudefinition des Effektmodells.

## Was genau eine Effekt-Datei sein koennte

Es gibt dafuer drei realistische Konzepte.

## Variante A: Gepackte Python-Effektdatei

Eine Effekt-Datei repraesentiert genau einen Effekt und enthaelt intern:

- Manifest
- Python-Implementierung
- optionale Assets
- Signatur oder Hash

Beispielstruktur innerhalb des Pakets:

```text
single-effect.lefx
  manifest.json
  effect.py
  assets/
    texture.bin
    palette.json
  signature.json
```

Vorteile:

- maximale Ausdrucksstaerke
- bestehende Python-Effektlogik laesst sich gut wiederverwenden
- komplexe Renderlogik bleibt moeglich

Nachteile:

- unsicherer, wenn fremder Python-Code geladen wird
- schwerer robust zu sandboxen
- Obfuskation ist nur begrenzt Schutz, eher Huerde

Einschaetzung:

Technisch am direktesten integrierbar, aber nur fuer vertrauenswuerdige Pakete sinnvoll.

## Variante B: Manifest plus Bytecode oder verschluesselter Renderer

Eine Effekt-Datei enthaelt:

- Manifest mit Definition und Metadaten
- kompilierten oder verschluesselten Renderer-Code
- optionale Assets
- Signatur

Beispiel:

```text
single-effect.lefx
  manifest.json
  renderer.pyc
  assets/
  signature.json
```

Vorteile:

- schwieriger direkt lesbar
- nah an deiner Anforderung nach nicht mehr lesbar oder aenderbar
- Verpackung als distributierbares Artefakt ist klar

Nachteile:

- Python-Bytecode ist nicht wirklich sicher
- Reverse Engineering bleibt moeglich
- Versions- und Plattformabhaengigkeiten werden unangenehmer
- Debugging und Support werden deutlich schwieriger

Einschaetzung:

Nur bedingt empfehlenswert, wenn das eigentliche Ziel eher Produktpaket statt Geheimhaltung ist.

## Variante C: Deklaratives Effektformat plus definierte Primitive

Eine Effekt-Datei enthaelt keinen freien Python-Code, sondern nur:

- Metadaten
- Parameterwerte
- Layerregeln
- eine deklarative Beschreibung aus einem begrenzten Bausteinsystem

Beispiel:

```json
{
  "format": "lefx/1",
  "effect_id": "call_active_main",
  "title": "Call Active Main",
  "target_layer": "main",
  "defaults": {
    "color": "#22AAFF",
    "period_ms": 1400
  },
  "pipeline": [
    { "op": "solid", "color": "#041018" },
    { "op": "pulse", "color": "#22AAFF", "period_ms": 1400, "mix": 0.85 }
  ]
}
```

Vorteile:

- sehr gut kontrollierbar
- kein beliebiger Fremdcode
- leichter validierbar
- sehr gut paketierbar und signierbar
- gut fuer Anwendungen mit wenigen, festen Effekten

Nachteile:

- weniger flexibel als freier Python-Code
- man muss eine kleine Effekt-DSL oder Primitive-Library definieren
- neue Renderideen brauchen neue Primitive im Service

Einschaetzung:

Das ist architektonisch die sauberste und langfristig robusteste Variante, wenn du vor allem vordefinierte, stabile, anwendungsnahe Effekte ausliefern willst.

## Meine Empfehlung

Ich wuerde einen hybriden Ansatz empfehlen.

### Empfohlener Zielzustand

Es gibt zwei Arten von Effektartefakten:

1. Entwicklungsformat
2. Laufzeitpaket

### Entwicklungsformat

Lesbar und editierbar.

Beispiel:

- Python-Effektmodul fuer interne Entwicklung
- oder deklaratives Manifest mit optionalen Assets

### Laufzeitpaket

Nicht fuer manuelle Bearbeitung gedacht.

Beispiel:

- `.lefx` fuer einen Effekt
- `.lefxset` fuer ein Effektset

Intern ist das einfach ein signiertes ZIP-basiertes Containerformat mit klarer Struktur.

Das wuerde ich nicht als echte Verschluesselung verkaufen, sondern als:

- Distributionsformat
- Integritaetsformat
- standardisierte Ladeeinheit

Wenn du echte Geheimhaltung willst, reicht normales Packaging nicht.
Dann brauchst du echte Verschluesselung, Schluesselverwaltung und ein Vertrauensmodell im Service. Das ist ein viel groesseres Thema.

## Wie ich die Dateitypen gestalten wuerde

## 1. Einzelne Effekt-Datei `.lefx`

Zweck:

- enthaelt genau einen konkret ausfuehrbaren Effekt

Moegliche Containerstruktur:

```text
my_effect.lefx
  manifest.json
  payload/
    effect.json
    assets/...
  signature.json
```

Pflichtinhalte im Manifest:

- Formatversion
- Paket-ID
- Effekt-ID
- Anzeigename
- Ziel-Layer oder erlaubte Layer
- Defaults
- Playback-Regeln
- Runtime-Typ
- Hashes der enthaltenen Dateien
- optionale Mindest-Service-Version

Sinnvolle Zusatzfelder:

- Hersteller oder Anwendung
- semantische Version
- Tags
- Kompatibilitaetsbereich
- Beschreibung
- Changelog oder Build-Metadaten

## 2. Effekt-Set-Datei `.lefxset`

Zweck:

- enthaelt mehrere `.lefx`-Einheiten oder mehrere Manifeste in einem Bundle

Containerstruktur:

```text
my_app_effects.lefxset
  set-manifest.json
  effects/
    listening_state.lefx
    transcribing_state.lefx
    wakeword_event.lefx
    timeout_overlay.lefx
  aliases.json
  signature.json
```

Set-Manifest sollte enthalten:

- Set-ID
- Anzeigename
- Version
- Liste enthaltener Effekte
- optionale Kategorien
- optionale Aliasnamen fuer die Anwendung
- Hashes oder Signaturen

## Was inhaltlich in einer Effekt-Datei drin sein sollte

Unabhaengig vom konkreten Verpackungsformat sollte ein Effektartefakt folgende Ebenen abdecken:

### A. Fachidentitaet

- stabile Effekt-ID innerhalb des Pakets
- menschenlesbarer Name
- Zweckbeschreibung
- Kategorie wie `state`, `main`, `event`, `temp_overlay`

### B. Runtime-Semantik

- Ziel-Layer oder erlaubte Layer
- Playback-Modus
- Dauerverhalten
- Queue-Regeln
- Transparenz oder Exklusivitaet
- Restorability

### C. Visuelle Parameter

- Farben
- Intensitaet oder Helligkeit
- Dauer
- Timing
- Richtung
- weitere konkrete Effektwerte

### D. Renderbeschreibung

Hier gibt es zwei Wege:

- deklarative Pipeline
- ausfuehrbarer Renderer

### E. Kompatibilitaetsmetadaten

- minimale Service-Version
- Formatversion
- optionale benoetigte Primitive
- optionale Hardware-Annahmen

### F. Integritaet

- Hash
- Signatur
- Build-Information

## Wie die Anwendung damit arbeiten koennte

Dein Ziel, dass die Anwendung nur noch einfache Befehle kennt, ist sinnvoll.

Dafuer wuerde ich zwei Namen unterscheiden:

1. interner Effektname
2. Anwendungsalias

Beispiel:

- technischer Effekt: `warning_flash_red_fast`
- Alias in der Anwendung: `mic_error`

Der Alias muss nicht Teil der Engine sein.
Er kann im Set-Manifest oder in einer Aliasdatei liegen.

Damit kann jede Anwendung ihren eigenen Kontext sprechen, ohne die technische Effekt-ID offenzulegen.

## Wie die Integration effizient aussehen koennte

Ich wuerde die Integration in vier Bausteinen denken.

## Baustein 1: Paketformat und Loader

Neues Modul, zum Beispiel sinngemaess:

- Paketdatei oeffnen
- Manifest validieren
- Signatur oder Hash pruefen
- Artefakt entpacken
- in registrierbare Runtime-Effekte uebersetzen

Wichtig:

Dieser Loader sollte nicht direkt in API oder CLI verstreut werden.
Er sollte ein klarer eigener Layer sein.

Zum Beispiel konzeptionell:

- `effect_package_loader`
- `effect_package_manifest`
- `effect_package_registry_adapter`

## Baustein 2: Registrierung im laufenden Service

Dafuer brauchst du tatsaechlich einen neuen Befehl oder mehrere.

Sinnvolle Service-Kommandos waeren hypothetisch:

- `register-effect-package <file>`
- `register-effect-set <file>`
- `register-effect-path <dir>` fuer Entwicklermodus
- `list-registered-effect-sources`
- `clear-effect-source <source_id>`

Ich wuerde aber Produktions- und Entwicklermodus unterscheiden.

### Entwicklermodus

- Ordnerpfad registrieren
- Autodiscovery erlauben
- Reload erlauben

### Produktionsmodus

- nur signierte `.lefx` oder `.lefxset`
- keine freien Quellordner
- optional nur registrierte Herausgeber

## Baustein 3: Packaging-CLI

Ein kleines, unabhaengiges CLI-Tool ist eine gute Idee.

Das Tool sollte nicht dieselbe CLI wie `main.py` sein, sondern ein eigenes Build-Werkzeug.

Beispielhafte Aufgaben:

- `pack-effect`
- `pack-effect-set`
- `inspect-effect-package`
- `verify-effect-package`
- `extract-effect-package` nur fuer autorisierte Entwickler

Wenn ihr spaeter Signaturen habt:

- `sign-effect-package`
- `verify-signature`

## Baustein 4: Alias- oder Befehlsmapping fuer Anwendungen

Anwendungen brauchen haeufig keine freie Effektwahl, sondern nur ein kleines Vokabular.

Dafuer wuerde ich ein Alias-Mapping pro Set vorsehen.

Beispiel:

```json
{
  "commands": {
    "idle": "state_idle_blue",
    "listening": "state_listening_soft",
    "transcribing": "state_transcribing_pulse",
    "error": "event_error_flash"
  }
}
```

Die Anwendung sendet dann nur:

- `invoke-command listening`
- oder intern eine Alias-Aufloesung zu einer Effekt-ID

Das ist naeher an deinem Ziel als die Anwendung direkt mit Parameterobjekten arbeiten zu lassen.

## Zentrale Architekturfrage: freier Code oder deklarative Dateien

Hier liegt die wichtigste Grundentscheidung.

## Option 1: freie Renderlogik in den Paketen

Dann koennen Pakete praktisch alles.

Das ist gut fuer maximale Flexibilitaet.

Aber:

- Sicherheitsrisiko
- schwieriger Betrieb
- schlechter validierbar
- schwerer portierbar

Diese Option passt nur, wenn alle Effektpakete aus vertrauenswuerdiger Quelle kommen.

## Option 2: deklaratives Effektformat

Dann definierst du einen festen Baukasten aus Primitive-Operationen.

Zum Beispiel:

- solid
- blink
- pulse
- countdown
- direction_marker
- progress_arc
- color_mix
- fade
- mask
- rotate

Dann enthalten die Dateien nur noch:

- Daten
- Ablaufbeschreibung
- feste Werte

Das ist fuer dein beschriebenes Anwendungsszenario wahrscheinlich effizienter.

Warum:

- wenige Effekte
- stark vordefiniert
- wenig dynamische Parameter
- klare Befehlssemantik
- kontrollierter Betrieb

## Deshalb meine bevorzugte Richtung

Wenn das Ziel wirklich ist:

- Anwendungslogik klein halten
- fertige Effekte mitliefern
- keine Parameterrumreicherei in der App
- nach Build nicht mehr normal editierbar
- effiziente Registrierung im Service

Dann ist ein deklaratives Paketformat plus Alias-Mapping sehr wahrscheinlich die beste Richtung.

## Ein moegliches konkretes Zielmodell

## Artefakt 1: `.lefx`

Enthaelt genau einen Effekt.

Interner Aufbau:

- `manifest.json`
- `effect.json`
- `assets/`
- `signature.json`

`effect.json` beschreibt einen Effekt deklarativ.

## Artefakt 2: `.lefxset`

Enthaelt mehrere Effekte plus Befehlsaliasse.

Interner Aufbau:

- `set-manifest.json`
- `effects/*.lefx`
- `commands.json`
- `signature.json`

## Service-seitige Verarbeitung

Beim Registrieren eines Sets passiert hypothetisch:

1. Datei oeffnen
2. Formatversion pruefen
3. Signatur oder Hash pruefen
4. enthaltene Effekte extrahieren
5. jeden Effekt in einen Runtime-Effekt uebersetzen
6. unter einer Source-ID registrieren
7. optionale Befehlsaliasse mitregistrieren

## API- und CLI-Erweiterungen, die ich mir vorstellen wuerde

Hypothetische API-Routen:

- `POST /api/v1/effect-sources/register-package`
- `POST /api/v1/effect-sources/register-set`
- `POST /api/v1/effect-sources/register-path`
- `GET /api/v1/effect-sources`
- `DELETE /api/v1/effect-sources/{source_id}`
- `GET /api/v1/effect-commands`
- `POST /api/v1/effect-commands/invoke`

Hypothetische CLI-Befehle:

- `register-effect-package <file>`
- `register-effect-set <file>`
- `register-effect-path <dir>`
- `list-effect-sources`
- `list-effect-commands`
- `invoke-effect-command <name>`

## Wichtige Risiken und Einwaende

## 1. Nicht lesbar oder nicht aenderbar ist technisch heikel formuliert

Wenn der Service die Datei lokal ausfuehren kann, kann ein technisch versierter Nutzer sie meistens auch irgendwann analysieren.

Deshalb sollte man sauber unterscheiden zwischen:

- nicht fuer manuelle Bearbeitung gedacht
- integritaetsgeschuetzt
- obfuskiert
- wirklich kryptografisch geschuetzt

Die letzte Variante ist deutlich aufwendiger.

## 2. Freier Python-Code in Paketen ist ein Sicherheitsproblem

Wenn externe Anwendungen Effektpakete mitliefern duerfen und diese Python-Code enthalten, fuehrt das praktisch auf Plugin-Code-Ausfuehrung hinaus.

Dann brauchst du mindestens:

- Vertrauensmodell
- Signaturen
- klare Zulassungsregeln
- moeglichst eingeschraenkte Ladepfade

## 3. Zu viel Intelligenz im Paketformat kann die Engine indirekt verdoppeln

Wenn das Paketformat zu maechig wird, baust du am Ende eine zweite Effekt-Engine im Paketformat.

Das sollte vermieden werden.

Darum lieber:

- kleine deklarative Primitive
- klarer Umfang
- wenige Sonderfaelle

## 4. Aliasnamen duerfen die technische Identitaet nicht ersetzen

Aliasnamen sind fuer Anwendungen gut.

Aber intern sollte der Service weiter mit stabilen Effekt-IDs und stabilen Source-IDs arbeiten.

Sonst wird Debugging unnötig schwer.

## Verbesserungsvorschlaege und Ergaenzungen

## Vorschlag A: zwischen App-Befehlen und Effekt-ID explizit unterscheiden

Das ist aus meiner Sicht sehr wichtig.

Nicht jede Anwendung braucht die technische Effekt-ID zu kennen.
Darum:

- Effekt-ID bleibt technisch
- App-Befehl bleibt fachlich
- das Mapping lebt im Set

## Vorschlag B: Sets versionieren und kompatibilitaetsfaehig machen

Ein Effekt-Set sollte immer haben:

- Set-Version
- minimale Service-Version
- optionale Migrationshinweise

So kann der Service bei Inkompatibilitaeten frueh und klar ablehnen.

## Vorschlag C: Source-Isolation pro Anwendung

Wenn mehrere Anwendungen denselben Service nutzen, sollte jede registrierte Effektquelle eine eigene Namespace-Identitaet bekommen.

Zum Beispiel:

- `app.voice_assistant`
- `app.factory_console`
- `app.demo_panel`

Dann kollidieren Effekt-IDs weniger leicht.

## Vorschlag D: readonly im Betrieb, aber Debug-Modus fuer Entwicklung

Ich wuerde zwei Modi einfuehren.

### Debug-Modus

- Rohformate erlaubt
- Ordner-Discovery erlaubt
- erweiterte Inspektion erlaubt

### Release-Modus

- nur `.lefx` oder `.lefxset`
- Signaturpruefung
- keine freien Python-Ordner
- kein unkontrollierter Reload

Das passt sehr gut zu deiner Grundidee.

## Vorschlag E: Effekte nicht nur als Visualisierung, sondern als Produktartefakt denken

Das ist wahrscheinlich die eigentliche Staerke deiner Idee.

Ein Effekt waere dann nicht mehr nur Code, sondern ein deploybares Produktartefakt mit:

- Identitaet
- Version
- Integritaet
- Befehlsalias
- Kompatibilitaet
- Visualisierung

Das ist architektonisch deutlich staerker als nur ein weiteres Python-Modul.

## Minimal sinnvoller Integrationspfad

Wenn man das effizient und risikoarm einfuehren will, wuerde ich nicht alles auf einmal bauen.

### Phase 1

Nur Set-Registrierung aus lesbaren Manifesten, noch ohne Verschluesselung.

Ziel:

- Konzept pruefen
- API und Registry testen
- Alias-Mapping testen

### Phase 2

ZIP-basiertes Paketformat `.lefx` und `.lefxset` mit Hashes und Signaturen.

Ziel:

- standardisierte Auslieferung
- Integritaetsschutz

### Phase 3

Optionaler Release-Modus mit restriktiver Paketannahme.

Ziel:

- kontrollierter Betrieb
- weniger freie Erweiterung im Produktivsystem

### Phase 4

Nur wenn wirklich notwendig:

- Obfuskation
- Verschluesselung
- Schluesselmanagement

Das wuerde ich nur angehen, wenn es dafuer einen echten Produktgrund gibt.

## Klare Empfehlung

Wenn ich das fuer dieses Repo entwerfen sollte, waere mein Vorschlag:

1. Effekt-Dateien nicht als Ersatz fuer `BaseEffect` bauen, sondern als Paketformat ueber der bestehenden Runtime.
2. Zunaechst kein freies verschluesseltes Python-Plugin-System bauen.
3. Stattdessen ein deklaratives Effektformat mit klaren Primitive-Bausteinen vorsehen.
4. Fuer Anwendungen ein Alias- oder Command-Mapping in Effekt-Sets einfuehren.
5. Registrierung ueber neue Source-Befehle und einen eigenen Package-Loader loesen.
6. Packaging in ein separates CLI-Tool auslagern.
7. Nicht mit Geheimhaltung argumentieren, sondern mit Integritaet, Distribution und Vereinfachung der App-Logik.

## Kurzfazit

Die Idee hat Substanz.

Der staerkste Kern daran ist nicht, dass ein Effekt in einer Datei liegt, sondern dass eine Anwendung ein fertiges, versioniertes, registrierbares Effektpaket oder Effektset mitbringen kann.

Wenn du das sauber aufziehst, gewinnst du:

- einfachere Anwendungen
- klarere Distributionswege
- besseres Source-Management
- kontrolliertere Integration externer Effektbestaende

Die aus meiner Sicht beste Form dafuer ist:

- lesbares Entwicklungsformat
- gepacktes Distributionsformat
- deklarative Effektbeschreibung, wo immer moeglich
- Alias-Mapping fuer anwendungsspezifische Befehle
- klarer Loader zwischen Paket und Runtime

Wenn man diesen Schnitt sauber haelt, ist das nicht nur machbar, sondern eine ziemlich starke Weiterentwicklung des aktuellen Systems.
