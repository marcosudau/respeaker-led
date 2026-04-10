# Komplett finales Konzept: Effekt-Dateien und Effekt-Set-Dateien

Stand: 2026-04-10
Status: finale Konzeptfassung fuer die experimentelle Umsetzung auf Branch `codex/effekt-dateien`

## 1. Einordnung und Ergebnis aus den letzten Anmerkungen

Die Anmerkungen aus `08__05_konzept_effekt_dateien.md` sind in den entscheidenden Punkten sinnvoll und verbessern das Konzept.

Insbesondere drei Punkte werden verbindlich uebernommen:

1. Registrierte Commands sind feste Befehle und keine parametrisierbaren Templates fuer Anwendungen.
2. Die Registrierung von Effektquellen soll nach aussen ueber genau eine einheitliche Route und einen einheitlichen CLI-Befehl laufen.
3. Paketquellen sollen in einer festen Autodiscovery-Struktur gefunden werden und nicht ueber eine separate Persistenzdatei wie `effect_sources.json`.

Zusatzbewertung zu den Anmerkungen:

- Die Rueckfrage zu `commands.json` war absolut berechtigt. Im vorherigen Stand war die Grenze zwischen internem Kommando-Profil und extern uebergebenem Payload zu weich formuliert.
- Die Idee einer vereinfachten Registrierungsroute ist sinnvoll und reduziert API- und CLI-Komplexitaet.
- Die vorgeschlagene Kommando-Struktur unter `/api/v1/commands/...` ist ebenfalls sinnvoll. Ich uebernehme sie im finalen Entwurf, mit der kleinen Korrektur, dass Auflistungen als `GET` und nicht als `POST` modelliert werden.

## 2. Zielbild

Die bestehende Runtime mit:

- `BaseEffect`
- `EffectDefinition`
- `EffectRegistry`
- `ControllerRuntime`
- `ControllerService`
- API und CLI

bleibt der fachliche Kern des Systems.

Neu hinzu kommt eine paketierte Distributions- und Registrierungsstruktur fuer Effekte:

- `.lefx` fuer genau einen Effekt
- `.lefxset` fuer eine registrierbare Effektquelle mit mehreren Effekten und festen Anwendungsbefehlen

Das Ziel ist:

- Anwendungen liefern fertige Effektartefakte mit.
- Der Service registriert diese Artefakte.
- Anwendungen sprechen nur noch ueber feste Commands.
- Anwendungen muessen keine Effektparameter mehr kennen oder senden.
- Die bestehende Runtime wird erweitert, nicht ersetzt.

## 3. Verbindliche Architekturentscheidungen

Die folgende Liste ist fuer die Umsetzung als verbindlich zu verstehen:

1. Effekt-Dateien werden als Distributionsformat ueber der bestehenden Runtime gebaut.
2. `.lefx` und `.lefxset` sind ZIP-basierte Container mit klarer Struktur.
3. Python-Logik in Effektpaketen bleibt erlaubt.
4. Die Grundversion fokussiert Funktionalitaet und Hash-basierte Integritaet, nicht strikte Signatur- oder Release-Haertung.
5. `qualified_effect_id` nach dem Schema `source_id::effect_id` wird eingefuehrt.
6. Anwendungen senden keine Effektparameter an registrierte Commands.
7. Commands sind feste, komplett definierte Aufrufe.
8. Registrierung nach aussen erfolgt ueber eine einzige Source-Registrierung.
9. Paketquellen werden nicht in `runtime_state/effect_sources.json` persistiert.
10. Paketquellen werden ueber einen festen Autodiscovery-Ordner erkannt.
11. Von Anfang an wird nur mit `.lefx` und `.lefxset` gearbeitet.
12. Die erste Packaging-CLI unterstuetzt nur `pack`, `inspect` und `verify`.

## 4. Ziel und Nicht-Ziel

### Ziele

- Anwendungen koennen eigene Effektbibliotheken als Pakete mitbringen.
- Der Service kann diese Pakete automatisch finden, pruefen und registrieren.
- Anwendungen arbeiten ausschliesslich mit festen Befehlen wie `listening`, `idle`, `mic_error`.
- Jeder Befehl steht fuer einen vollstaendig definierten Effektaufruf.
- Die bestehende Effect-Runtime bleibt erhalten.
- Paketquellen sind namespaced und kollisionsarm.

### Nicht-Ziele

- Keine echte Verschluesselung oder Geheimhaltung
- Kein untrusted Plugin-Sandboxing
- Kein generisches Parameter-API fuer registrierte Commands
- Keine Persistenz explizit registrierter Effektquellen ausserhalb der Autodiscovery-Struktur in der Grundversion

## 5. Grundmodell: Effekt, Quelle, Command

Das finale Konzept unterscheidet drei Ebenen sauber:

### 5.1 Einzelner Effekt

Ein Effekt ist ein technischer Runtime-Baustein.

Er besteht weiterhin aus:

- einer `BaseEffect`-Unterklasse
- ihrer `EffectDefinition`
- ihrer Renderlogik

Er wird intern ueber eine qualifizierte technische ID adressiert:

```text
<source_id>::<effect_id>
```

Beispiel:

```text
app.voice_assistant::listening_blue
```

### 5.2 Effektquelle

Eine Effektquelle ist eine logisch zusammengehoerige Bibliothek von Effekten.

Sie wird in der Regel durch ein `.lefxset` repraesentiert.

Beispiele:

- `builtin.default-effects`
- `app.voice_assistant`
- `app.demo_panel`

### 5.3 Command

Ein Command ist kein allgemeiner Effektaufruf und kein Template.

Ein Command ist ein fest definierter, anwendungsnaher Befehl, der intern auf genau eine definierte Aktion abgebildet wird.

Beispiele:

- `idle`
- `listening`
- `transcribing`
- `mic_error`

Ein Command definiert insbesondere fest:

- welcher Effekt oder welche Aktion ausgefuehrt wird
- auf welchem Layer dies geschieht
- welche Parameter intern gesetzt werden
- ob das Kommando schaltbar ist
- wie `off` umgesetzt wird

Wichtig:

Die Anwendung darf diese Parameter nicht mehr veraendern.

Wenn dieselbe visuelle Logik in anderer Farbe oder anderer Dauer gebraucht wird, ist das kein anderer Payload, sondern ein anderer Command oder ein anderer Effekt.

## 6. Dateiformate

## 6.1 `.lefx`

`.lefx` ist ein ZIP-Container fuer genau einen Effekt.

Vorgeschlagene Struktur:

```text
my_effect.lefx
  manifest.json
  payload/
    effect.py
    assets/
      ...
  hashes.json
```

`signature.json` ist fuer eine spaetere Haertungsphase vorgesehen, aber nicht verpflichtender Teil der Grundversion.

### `manifest.json`

Pflichtfelder:

- `format`: `"lefx/1"`
- `package_id`
- `source_id`
- `effect_id`
- `qualified_effect_id`
- `title`
- `description`
- `version`
- `runtime`: `"python_base_effect/1"`
- `entry_module`
- `entry_class`
- `defaults`
- `parameter_schema`
- `layer_rules`
- `capabilities`
- `min_service_version`

Optionale Felder:

- `tags`
- `author`
- `vendor`
- `build_meta`
- `created_at`
- `compatible_hardware`
- `license`

### Python-Payload

`payload/effect.py` stellt die konkrete `BaseEffect`-Unterklasse bereit.

Der Loader verwendet explizit:

- `entry_module`
- `entry_class`

Es gibt keine freie Symbol-Discovery innerhalb eines Pakets.

## 6.2 `.lefxset`

`.lefxset` ist ein ZIP-Container fuer eine registrierbare Effektquelle inklusive Commands.

Vorgeschlagene Struktur:

```text
my_app_effects.lefxset
  set-manifest.json
  effects/
    idle_blue.lefx
    listening_blue.lefx
    transcribing_pulse.lefx
    mic_error_flash.lefx
  commands.json
  hashes.json
```

### `set-manifest.json`

Pflichtfelder:

- `format`: `"lefxset/1"`
- `set_id`
- `source_id`
- `title`
- `version`
- `min_service_version`
- `effects`

Optionale Felder:

- `description`
- `tags`
- `author`
- `vendor`
- `command_namespace`

## 6.3 `commands.json`

`commands.json` beschreibt das fachliche Vokabular der Anwendung.

Im finalen Modell sind diese Commands fest definiert und nicht mehr durch App-Payload veraenderbar.

### Prinzip

`commands.json` enthaelt nicht nur die Namen der Commands, sondern die vollstaendige interne Abbildung jedes Commands.

Jeder Command ist damit ein festes Runtime-Profil.

### Beispielschema

```json
{
  "namespace": "voice_assistant",
  "commands": {
    "idle": {
      "kind": "state_toggle",
      "on": {
        "effect": "app.voice_assistant::idle_blue",
        "target_layer": "STATE_LAYER",
        "params": {},
        "replace_existing": true
      },
      "off": {
        "action": "clear_layer",
        "target_layer": "STATE_LAYER"
      }
    },
    "listening": {
      "kind": "state_toggle",
      "on": {
        "effect": "app.voice_assistant::listening_blue",
        "target_layer": "MAIN_LAYER",
        "params": {}
      },
      "off": {
        "action": "clear_layer",
        "target_layer": "MAIN_LAYER"
      }
    },
    "mic_error": {
      "kind": "event",
      "on": {
        "effect": "app.voice_assistant::mic_error_flash",
        "target_layer": "EVENT_LAYER",
        "params": {}
      }
    }
  }
}
```

### Bedeutung

- `kind="state_toggle"` bedeutet: Das Command kann auf `on` und `off` abgebildet werden.
- `kind="event"` bedeutet: Das Command ist ein einmaliger Trigger ohne sinnvolles `off`.
- `params` sind intern im Paket fixiert.
- `replace_existing` ist in der Praxis fest und muss nicht von aussen konfigurierbar sein.

### Wichtige Konsequenz

Die Anwendung sendet fuer registrierte Commands:

- keinen `payload`
- keine Farbe
- keine Dauer
- kein `replace_existing`

Alles davon steckt bereits fest im Paket und im Command-Profil.

Wenn eine Variante in anderer Farbe gebraucht wird, dann wird dafuer ein eigener Effekt und ein eigener Command definiert.

## 6.4 Hashes

Die Grundversion sichert Integritaet ueber `hashes.json`.

Beispiel:

```json
{
  "algorithm": "sha256",
  "files": {
    "manifest.json": "abc123...",
    "payload/effect.py": "def456..."
  }
}
```

Die erste funktionsfaehige Version verlangt:

- gueltige ZIP-Struktur
- gueltige Manifeste
- vorhandene referenzierte Dateien
- passende Hashes

Signaturen sind als spaetere Erweiterung eingeplant, aber kein Blocker fuer die erste Umsetzung.

## 7. Autodiscovery-Modell

Die Anmerkung gegen `effect_sources.json` wird uebernommen.

In der Grundversion werden Paketquellen nicht separat persistent registriert, sondern ueber eine definierte Ordnerstruktur gefunden.

## 7.1 Autodiscovery-Wurzel

Empfohlener neuer Paketordner:

```text
led_effects/packages/
```

Dort duerfen liegen:

- einzelne `.lefx`
- `.lefxset`

## 7.2 Discovery-Regeln

Beim Aufbau oder Reload der Registry gilt:

1. Builtins aus `led_effects/effects/` werden wie bisher geladen.
2. Danach werden Pakete aus `led_effects/packages/` rekursiv gesucht.
3. Jede `.lefx` wird als einzelne Paketquelle geladen.
4. Jede `.lefxset` wird als komplette Effektquelle geladen.

### Konfliktregel

Wenn zwei Paketquellen dieselbe `source_id` oder dieselbe `qualified_effect_id` erzeugen, ist das ein harter Fehler.

## 7.3 Warum kein `effect_sources.json`

Fuer die Grundversion ist die Autodiscovery robuster und einfacher:

- kein zusaetzlicher Persistenzpfad
- keine Synchronisationsprobleme zwischen Dateiablage und Registrierungsdatei
- besser nachvollziehbar fuer Entwicklung und Deployment

Wenn spaeter eine explizite Source-Verwaltung gebraucht wird, kann das zusaetzlich kommen.

## 8. Integration in die bestehende Codebasis

## 8.1 Bestehende Andockpunkte

Die relevanten Stellen im Repo bleiben:

- `src/effect_schema.py`
- `src/effect_registry.py`
- `src/runtime.py`
- `src/service.py`
- `src/api.py`
- `src/cli.py`
- `src/paths.py`
- `tests/test_effect_registry.py`
- `tests/test_api.py`
- `tests/test_cli.py`

## 8.2 Neue Module

Fuer die Umsetzung werden mindestens diese neuen Module empfohlen:

- `src/effect_package_schema.py`
- `src/effect_package_loader.py`
- `src/effect_package_builder.py`
- `src/effect_command_registry.py`

Spaeter optional:

- `src/effect_signature.py`

Nicht Teil der Grundversion:

- `src/effect_source_store.py`

## 8.3 Erweiterung von `src/paths.py`

Empfohlene neue Pfade:

- `EFFECT_PACKAGES_ROOT = LED_EFFECTS_ROOT / "packages"`

Damit werden Builtin-Effekte und Paketquellen klar getrennt:

- `led_effects/effects/`
- `led_effects/packages/`

## 8.4 Erweiterung von `EffectRegistry`

Die Registry bleibt der zentrale Integrationspunkt.

Sie soll kuenftig drei Quellarten beherrschen:

1. manuell registrierte Effektklassen
2. Builtin-Library-Pfade
3. Paketquellen aus `.lefx` und `.lefxset`

### Neue Source-Kinds

- `library_path`
- `effect_package`
- `effect_set`

### Neue Registry-Methoden

Nach aussen soll das Modell einfach bleiben. Intern sind aber diese Methoden sinnvoll:

- `register_effect_package(path, *, enabled=True)`
- `register_effect_set(path, *, enabled=True)`
- `register_effect_source(path, *, enabled=True)`
- `list_effect_sources()`
- `list_effect_commands(source_id=None)`
- `invoke_command(source_id, command_name, state=None)`
- `reload()`

### `register_effect_source(...)`

Diese Methode ist die einheitliche Fachschnittstelle.

Intern erkennt sie anhand des Dateiformats:

- `.lefx`
- `.lefxset`

### Lookup-Regel

Neue Paketquellen werden ueber `qualified_effect_id` adressiert.

Builtins duerfen zur Abwaertskompatibilitaet weiterhin ueber bare `effect_id` adressierbar bleiben.

## 8.5 Runtime-Auswirkungen

Die Runtime selbst bleibt weitgehend unveraendert.

Sie muss nur damit umgehen koennen, dass Effekt-IDs kuenftig qualifiziert sein koennen.

Noetige Anpassungen:

- `apply_effect(...)` akzeptiert `qualified_effect_id`
- Status-Snapshots koennen `qualified_effect_id` mit ausgeben
- Persistenz von Background-State bleibt moeglich, auch mit qualifizierten IDs

Die Runtime selbst muss keine Paketdateien kennen.

## 8.6 Command-Registry

Zusatzlich zur Effekt-Registry braucht es eine Command-Registry.

Diese verwaltet pro `source_id`:

- verfuegbare Commands
- Command-Typ
- `on`-Definition
- `off`-Definition

Sie bildet die Bruecke zwischen API/CLI-Befehl und internem Effektaufruf.

## 9. Finale API-Struktur

Die bisherige API bleibt in ihrer Grundstruktur erhalten.

Neu hinzu kommen Paket- und Command-Routen.

## 9.1 Effektquellen

### Quellen auflisten

- `GET /api/v1/effect-sources`

### Quelle registrieren

- `POST /api/v1/effect-sources/register`

Request-Beispiel:

```json
{
  "path": "C:/apps/voice_assistant/effects/voice_assistant.lefxset",
  "enabled": true
}
```

Intern wird anhand der Dateiendung entschieden, ob `.lefx` oder `.lefxset` geladen wird.

### Quellen neu laden

- `POST /api/v1/effect-sources/reload`

### Quelle entfernen

- `DELETE /api/v1/effect-sources/{source_id}`

## 9.2 Commands

Hier wird deine vorgeschlagene Richtung uebernommen, aber REST-sauber ausformuliert.

### Alle verfuegbaren Commands auflisten

- `GET /api/v1/commands`

### Commands einer Quelle auflisten

- `GET /api/v1/commands/{source_id}`

### Details eines Commands

- `GET /api/v1/commands/{source_id}/{command_name}`

### Basisaufruf eines Commands

- `POST /api/v1/commands/{source_id}/{command_name}`

Semantik:

- bei `state_toggle`: toggle zwischen `on` und `off`
- bei `event`: fuehre `on` aus

### Eindeutig auf `on`

- `POST /api/v1/commands/{source_id}/{command_name}/on`

### Eindeutig auf `off`

- `POST /api/v1/commands/{source_id}/{command_name}/off`

`/off` ist nur fuer Commands gueltig, die eine `off`-Definition besitzen.

### Kein Payload fuer Commands

Die Command-Routen bekommen in der Grundversion keinen variablen Effekt-Payload.

Das ist eine der bewusst zentralen Vereinfachungen dieses Konzepts.

## 9.3 Bestehende Effekt-Route

`GET /api/v1/effects` bleibt erhalten und wird erweitert um:

- `id`
- `qualified_id`
- `source_id`
- `source_kind`
- `package_id`
- `package_version`

## 10. Finale CLI-Struktur

Die Service-CLI bleibt in `src/cli.py`.

## 10.1 Paketquellen

- `list-effect-sources`
- `register-effect-source <file>`
- `reload-effect-sources`
- `remove-effect-source <source_id>`

Die getrennten Varianten `register-effect-package` und `register-effect-set` sind intern noch moeglich, aber nicht mehr die bevorzugte aussen sichtbare Schnittstelle.

## 10.2 Commands

- `list-commands`
- `list-commands --source app.voice_assistant`
- `invoke-command app.voice_assistant listening`
- `invoke-command app.voice_assistant listening on`
- `invoke-command app.voice_assistant listening off`

Auch hier gilt:

- kein Command-Payload
- keine frei uebergebenen Parameter

## 10.3 Packaging-CLI

Die Packaging-Funktionalitaet bleibt in einem separaten Tool, zum Beispiel:

```text
tools/effect_packager.py
```

Die erste Version soll nur diese Kommandos unterstuetzen:

- `pack-effect`
- `pack-effect-set`
- `inspect-effect-package`
- `verify-effect-package`

Nicht Teil der ersten Version:

- `extract`
- `sign`

## 11. Service- und CLI-Semantik fuer Commands

Die entscheidende fachliche Regel lautet:

Registrierte Commands sind kein Ersatz fuer `apply_effect(...)`, sondern eine eigene, feste Bedienoberflaeche fuer Anwendungen.

### 11.1 `state_toggle`

Geeignet fuer:

- `idle`
- `listening`
- `transcribing`

Semantik:

- `POST /api/v1/commands/{source_id}/{command_name}` togglet
- `.../on` setzt sicher auf aktiv
- `.../off` setzt sicher auf inaktiv

Typische `off`-Aktion:

- `clear_layer` des definierten Layers

### 11.2 `event`

Geeignet fuer:

- `mic_error`
- `wakeword_detected`
- `timeout_warning`

Semantik:

- Basisroute fuehrt das Event aus
- `off` ist nicht gueltig

## 12. Sicherheits- und Betriebsmodell

## 12.1 Grundversion

Die Grundversion ist ein funktionaler MVP.

Sie verlangt:

- valides Paketformat
- korrekte Hashes
- konsistente Manifeste
- gueltige `BaseEffect`-Klassen

Sie verlangt noch nicht:

- verpflichtende Signaturpruefung
- Trust Store
- harten Release-Modus

## 12.2 Spaetere Haertungsphase

Spaeter koennen ergaenzt werden:

- `signature.json`
- Trust Store
- Release-Mode-Flag
- restriktive Annahmeregeln fuer nur signierte Pakete

Das ist aber bewusst nicht Teil des ersten Implementierungsziels.

## 13. Implementierungsplan

Der Plan wird an den finalen Entscheidungen ausgerichtet.

## Phase 1: Paket-Schemata und Hash-Validierung

Ziel:

- formale Modelle fuer `.lefx`, `.lefxset`, `commands.json` und `hashes.json`

Arbeitspakete:

- `effect_package_schema.py`
- Manifest-Parser
- Set-Manifest-Parser
- Command-Schema
- Hash-Validierung

Tests:

- positive und negative Manifest-Tests
- `commands.json`-Validierung
- Hash-Fehlerszenarien

## Phase 2: Loader fuer `.lefx`

Ziel:

- einzelne Effektpakete laden und validieren

Arbeitspakete:

- ZIP-Lesen
- Datei-Existenz pruefen
- Hashes pruefen
- Python-Payload importieren
- Entry-Klasse pruefen
- Manifest gegen `EffectDefinition` pruefen

Tests:

- Loader-Tests fuer gueltige und ungueltige `.lefx`

## Phase 3: Loader fuer `.lefxset` und Command-Model

Ziel:

- Sets mit mehreren Effekten und Commands laden

Arbeitspakete:

- `.lefxset` lesen
- enthaltene `.lefx` laden
- `commands.json` parsen
- Command-Registry-Modell bauen

Tests:

- Set-Loader-Tests
- Konflikttests fuer doppelte Commands
- Tests fuer ungueltige `on`- und `off`-Definitionen

## Phase 4: Registry-Integration und Autodiscovery

Ziel:

- Paketquellen in die bestehende Registry integrieren

Arbeitspakete:

- `EFFECT_PACKAGES_ROOT` in `src/paths.py`
- Discovery aus `led_effects/packages/`
- `register_effect_source(...)`
- `list_effect_sources()`
- `list_effect_commands()`

Tests:

- Ausbau von `tests/test_effect_registry.py`
- Tests fuer Discovery, Konflikte, Reload, gemischte Quellen

## Phase 5: Service und API

Ziel:

- Registrieren, Auflisten und Aufrufen ueber die HTTP-API

Arbeitspakete:

- Service-Methoden fuer Sources und Commands
- API-Modelle fuer Source-Registrierung
- neue `/api/v1/effect-sources/...`-Routen
- neue `/api/v1/commands/...`-Routen

Tests:

- Ausbau von `tests/test_api.py`
- Toggle-, `on`-, `off`- und Event-Tests

## Phase 6: CLI und Client

Ziel:

- dieselbe Funktionalitaet ueber CLI verfuergbar machen

Arbeitspakete:

- neue CLI-Befehle
- Client-Methoden fuer Source-Registrierung und Command-Aufruf

Tests:

- Ausbau von `tests/test_cli.py`
- Ausbau von `tests/test_client.py`

## Phase 7: Packaging-CLI

Ziel:

- aus lesbaren Quellordnern `.lefx` und `.lefxset` bauen

Arbeitspakete:

- `tools/effect_packager.py`
- `pack-effect`
- `pack-effect-set`
- `inspect-effect-package`
- `verify-effect-package`

Tests:

- Roundtrip-Tests:
  Entwicklungsformat -> Paket -> Loader -> Registry

## Phase 8: Dokumentation und Beispielpakete

Ziel:

- System fuer spaetere Umsetzung und Benutzung dokumentieren

Arbeitspakete:

- `docs/effects.md` erweitern
- API- und CLI-Doku erweitern
- Beispielpakete anlegen

Tests:

- Doku-Beispiele gegen echte CLI/API pruefen

## Phase 9: Spaetere Haertung

Ziel:

- Signatur- und Release-Regeln nachziehen

Arbeitspakete:

- `signature.json`
- Trust Store
- Release-Mode

Tests:

- Signaturtests
- Ablehnung unsignierter Pakete im Release-Modus

## 14. Teststrategie

Fuer die spaetere Umsetzung gilt weiterhin:

- Paket-Schemata unit-testen
- Loader unit- und integrationsnah testen
- Registry, API, CLI und Client durchgaengig testen
- gesamtes `pytest -q` mitlaufen lassen

Besonders wichtig fuer dieses Vorhaben:

- Tests fuer feste Command-Semantik ohne Payload
- Tests fuer Toggle- und On/Off-Verhalten
- Tests fuer Discovery aus `led_effects/packages/`
- Tests fuer Konflikte bei `source_id` und `qualified_effect_id`

## 15. Zusammenfassung des finalen Zielmodells

Das jetzt wirklich finale Zielmodell lautet:

- Die bestehende Python-Runtime bleibt erhalten.
- Einzelne Effekte werden als `.lefx` ausgeliefert.
- Effektquellen mit Commands werden als `.lefxset` ausgeliefert.
- Commands sind feste, nicht parametrisierbare Anwendungsbefehle.
- Anwendungen sprechen nur noch diese Commands an.
- Die Registrierung erfolgt ueber eine einheitliche Source-Schnittstelle.
- Paketquellen werden ueber `led_effects/packages/` automatisch entdeckt.
- Die Grundversion setzt auf Funktionalitaet und Hash-Integritaet.
- Signaturen und strikter Release-Modus kommen spaeter als Haertungsphase.

Damit ist das Konzept jetzt so weit konkretisiert, dass als naechster Schritt direkt die technische Umsetzung entlang dieses Entwurfs beginnen kann.
