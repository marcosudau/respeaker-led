# Finales Gesamtkonzept: Effekt-Dateien und Effekt-Set-Dateien

Stand: 2026-04-10
Status: finaler Konzeptentwurf fuer experimentelle Umsetzung auf Branch `codex/effekt-dateien`

Hinweis zum heutigen Stand:

Das Dokument bleibt als Konzeptstand erhalten. Die spaetere Implementierung hat jedoch die hier noch diskutierten Rohquellpfade verworfen und registriert Effektquellen heute ausschliesslich als `.lefx`- oder `.lefxset`-Artefakte.
Auch die hier diskutierten Persistenzpfade unter `runtime_state/` sind deshalb als Konzeptstand zu lesen, nicht als aktuelle Laufzeitorte.

## 1. Zielbild

Die bestehende Runtime mit `BaseEffect`, `EffectDefinition`, `EffectRegistry`, `ControllerRuntime`, API und CLI bleibt der fachliche Kern des Systems.

Neu hinzu kommt eine paketierte Distributionsschicht fuer Effekte:

- `.lefx` enthaelt genau einen distributierbaren Effekt
- `.lefxset` enthaelt mehrere `.lefx`-Artefakte plus anwendungsnahe Befehlsaliasse

Diese Artefakte sollen:

- von Anwendungen als fertige Effektbibliothek mitgeliefert werden koennen
- registrierbar, versionierbar und pruefbar sein
- Integritaet absichern, aber keine Geheimhaltung versprechen
- komplexe Effekte mit individueller Python-Logik weiterhin erlauben
- App-seitig ein einfaches Befehlsvokabular ermoeglichen
- die bestehende Runtime erweitern, nicht ersetzen

## 2. Verbindliche Architekturentscheidungen

Aus dem bisherigen Planungsverlauf und den Folgeanweisungen ergeben sich fuer das finale Konzept diese verbindlichen Leitentscheidungen:

1. Effekt-Dateien werden nicht als Ersatz des heutigen Runtime-Modells entworfen, sondern als Distributions- und Registrierungsformat oberhalb der bestehenden Runtime.
2. `.lefx` und `.lefxset` werden als ZIP-basierte Containerformate mit klarer Struktur definiert.
3. Die urspruengliche Idee einer echten Verschluesselung oder Geheimhaltung wird verworfen.
4. Integritaet und Herkunft sollen dennoch abgesichert werden, also ueber Hashes und Signaturen.
5. Freie Python-Renderlogik in Effektpaketen bleibt explizit erlaubt.
6. Zwischen technischer Effektidentitaet und anwendungsnahem Befehl wird sauber getrennt.
7. Effektquellen werden source-basiert isoliert gedacht.
8. Debug- und Release-Betrieb werden bewusst unterschieden.
9. Ein eigenes Packaging-Werkzeug gehoert zum Konzept dazu und wird nicht in die bestehende Service-CLI hineingezogen.

## 3. Ziel und Nicht-Ziel

### Ziele

- Anwendungen koennen vorgefertigte Effekte oder Effektsets mitliefern.
- Der Service kann diese Artefakte registrieren, auflisten, entladen und wieder laden.
- Anwendungen muessen nicht mehr rohe Effektparameter und interne Effekt-IDs im Detail kennen.
- Alias-Befehle koennen app-spezifisch auf technische Effekte gemappt werden.
- Die Runtime behaelt ihr etabliertes Modell aus `EffectDefinition`, Registry, Invocation und Rendering.
- Effektquellen werden nachvollziehbar versioniert und mit Integritaetsmetadaten versehen.

### Nicht-Ziele

- Kein echtes DRM- oder Verschluesselungssystem
- Kein generisches Plugin-Sandboxing fuer untrusted Code
- Kein kompletter Umbau der Effekt-Engine
- Keine zweite, parallel maechige Effekt-DSL neben Python in der ersten Ausbaustufe

## 4. Architekturgrundsaetze

### 4.1 Drei Ebenen bleiben getrennt

Das Konzept trennt strikt zwischen:

1. Laufzeitmodell
2. Entwicklungsformat
3. Distributionsformat

Die Laufzeit bleibt Python-basiert und verwendet weiterhin `BaseEffect`, `EffectDefinition`, `RenderContext` und `EffectRegistry`.

Das Entwicklungsformat bleibt lesbar und editierbar.

Das Distributionsformat ist eine standardisierte, verifizierbare Ladeeinheit fuer Registrierung und Deployment.

### 4.2 Technische Identitaet und App-Befehl sind nicht dasselbe

Ein technischer Effekt behaelt seine eigene technische Identitaet.

Ein Anwendungskommando ist ein separates Alias, das in einem `.lefxset` definiert wird.

Beispiel:

- technischer Effekt: `warning_flash_red_fast`
- registrierter Runtime-Key: `app.voice_assistant::warning_flash_red_fast`
- App-Befehl: `mic_error`

### 4.3 Source-Isolation ist Pflicht

Effekte aus verschiedenen Quellen duerfen sich nicht implizit gegenseitig ueberschreiben.

Darum wird jede registrierte Quelle durch eine `source_id` repraesentiert, zum Beispiel:

- `builtin.default-effects`
- `app.voice_assistant`
- `app.demo_panel`

Aus `source_id` und paketlokaler `effect_id` entsteht ein qualifizierter Runtime-Key:

- `builtin.default-effects::solid_color`
- `app.voice_assistant::listening_soft`

### 4.4 Debug- und Release-Modus werden unterschieden

Debug-Modus:

- Registrierung lesbarer Entwicklungsordner erlaubt
- Inspektion und Extraktion erlaubt
- Signaturpruefung optional oder lockerer

Release-Modus:

- nur `.lefx` und `.lefxset`
- Integritaetspruefung verpflichtend
- Signaturpruefung verpflichtend
- keine freien Entwicklungsordner
- keine unkontrollierte Modul-Discovery ausserhalb expliziter Effektquellen

## 5. Formales Modell der Artefakte

## 5.1 Entwicklungsformat

Das Entwicklungsformat ist fuer Autoren und interne Entwicklung gedacht.

Es bleibt bewusst lesbar.

Empfohlene Struktur fuer einen einzelnen Effekt:

```text
effect_src/
  effect.yaml
  effect.py
  assets/
    palette.json
    texture.bin
```

Empfohlene Struktur fuer ein Effektset:

```text
effect_set_src/
  set.yaml
  commands.json
  effects/
    listening/
      effect.yaml
      effect.py
      assets/
    transcribing/
      effect.yaml
      effect.py
```

### `effect.yaml` im Entwicklungsformat

Pflichtfelder:

- `format_version`
- `package_id`
- `effect_id`
- `title`
- `description`
- `entry_module`
- `entry_class`
- `version`
- `source_id`
- `runtime`
- `defaults`
- `parameter_schema`
- `layer_rules`
- `capabilities`

Optionale Felder:

- `tags`
- `min_service_version`
- `author`
- `vendor`
- `homepage`
- `build`
- `assets`

### `set.yaml` im Entwicklungsformat

Pflichtfelder:

- `format_version`
- `set_id`
- `title`
- `version`
- `source_id`
- `effects`

Optionale Felder:

- `description`
- `min_service_version`
- `commands`
- `tags`
- `author`
- `vendor`

## 5.2 Distributionsformat `.lefx`

`.lefx` ist ein ZIP-Container fuer genau einen Effekt.

Vorgeschlagene Containerstruktur:

```text
my_effect.lefx
  manifest.json
  payload/
    effect.py
    assets/
      ...
  hashes.json
  signature.json
```

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
- `entry_module`: `"payload.effect"`
- `entry_class`
- `defaults`
- `parameter_schema`
- `layer_rules`
- `capabilities`
- `min_service_version`
- `artifact_hashes`

Optionale Felder:

- `tags`
- `author`
- `vendor`
- `build_meta`
- `created_at`
- `compatible_hardware`
- `license`

### `qualified_effect_id`

Dieses Feld wird bereits im Paket fixiert, damit spaeter:

- Kollisionen vermieden werden
- Logs und API-Antworten stabil bleiben
- Alias-Mappings eindeutig aufloesen koennen

Schema:

```text
<source_id>::<effect_id>
```

### Python-Payload

`payload/effect.py` muss eine konkrete `BaseEffect`-Unterklasse bereitstellen.

Der Loader importiert nicht beliebige Symbolnamen per Discovery, sondern genau die in `manifest.json` hinterlegte Entry-Definition:

- `entry_module`
- `entry_class`

Dadurch bleibt das Paketmodell explizit und validierbar.

## 5.3 Distributionsformat `.lefxset`

`.lefxset` ist ein ZIP-Container fuer eine registrierbare Effektquelle mit mehreren Effekten und optionalem Befehlsvokabular.

Vorgeschlagene Containerstruktur:

```text
my_app_effects.lefxset
  set-manifest.json
  effects/
    listening.lefx
    transcribing.lefx
    timeout_overlay.lefx
  commands.json
  hashes.json
  signature.json
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
- `artifact_hashes`

Optionale Felder:

- `description`
- `tags`
- `author`
- `vendor`
- `command_namespace`
- `default_release_mode`

### `effects`

Liste der enthaltenen Effektartefakte mit:

- Dateiname
- `package_id`
- `effect_id`
- `qualified_effect_id`
- Version

### `commands.json`

`commands.json` repraesentiert das fachliche Vokabular der Anwendung.

Empfohlenes Schema:

```json
{
  "namespace": "voice_assistant",
  "commands": {
    "idle": {
      "effect": "app.voice_assistant::idle_blue",
      "target_layer": "STATE_LAYER",
      "default_params": {}
    },
    "listening": {
      "effect": "app.voice_assistant::listening_soft",
      "target_layer": "MAIN_LAYER",
      "default_params": {
        "color": "#22AAFF"
      }
    },
    "mic_error": {
      "effect": "app.voice_assistant::warning_flash_red_fast",
      "target_layer": "EVENT_LAYER",
      "default_params": {
        "duration_ms": 1200
      }
    }
  }
}
```

## 5.4 Hashes und Signaturen

### Integritaetsmodell

Es gibt bewusst zwei Ebenen:

1. Dateiintegritaet ueber Hashes
2. Herkunftspruefung ueber Signaturen

### `hashes.json`

Enthaelt fuer jede enthaltene Datei einen SHA-256 Hash.

Beispiel:

```json
{
  "algorithm": "sha256",
  "files": {
    "manifest.json": "abc123...",
    "payload/effect.py": "def456...",
    "payload/assets/palette.json": "ghi789..."
  }
}
```

### `signature.json`

Empfohlener Zielstandard:

- Algorithmus: `ed25519`
- Signiert wird ein kanonischer Hash ueber `manifest.json` und `hashes.json`
- Der Service prueft gegen einen konfigurierten Trust Store

Wichtig:

- Signatur bedeutet Herkunft und Unveraendertheit
- Signatur bedeutet nicht Geheimhaltung

## 5.5 Formale Validierungsregeln

Ein Paket ist nur gueltig, wenn:

1. das Containerformat syntaktisch stimmt
2. alle Pflichtdateien vorhanden sind
3. `manifest.json` oder `set-manifest.json` parsebar ist
4. alle referenzierten Dateien existieren
5. alle Hashes passen
6. die Signatur im Release-Modus gueltig ist
7. `min_service_version` kompatibel ist
8. `qualified_effect_id` zum Schema `<source_id>::<effect_id>` passt
9. die geladene Effektklasse eine valide `BaseEffect`-Unterklasse ist
10. die `EffectDefinition` der geladenen Klasse mit den deklarativen Manifestfeldern konsistent ist

Der Loader soll Manifest und geladene Klasse gegeneinander pruefen.

Beispiele fuer harte Fehler:

- `effect_id` in Manifest stimmt nicht mit `definition.id` der Klasse ueberein
- `entry_class` existiert nicht
- qualifizierte ID kollidiert mit bereits registrierter Quelle
- Signatur ist ungueltig

## 6. Integration in die bestehende Codebasis

## 6.1 Bestehende relevante Architektur

Heute sind die wichtigen Andockpunkte:

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

Die aktuelle Architektur laedt Effektklassen dateibasiert aus `led_effects/effects/` und registriert sie in `EffectRegistry`.

Das neue Konzept erweitert genau diese Registry um neue Source-Arten.

## 6.2 Neue fachliche Bausteine

Es werden folgende neuen Module vorgeschlagen:

- `src/effect_package_schema.py`
- `src/effect_package_loader.py`
- `src/effect_package_builder.py`
- `src/effect_command_registry.py`
- `src/effect_source_store.py`

Optional spaeter:

- `src/effect_signature.py`
- `src/effect_package_cache.py`

### Aufgaben der Module

`effect_package_schema.py`

- Dataklassen fuer Manifest, Set-Manifest, Command-Mapping, Verify-Result
- Parser und Schema-Validierung

`effect_package_loader.py`

- `.lefx` und `.lefxset` oeffnen
- Hashes pruefen
- Signatur pruefen
- Python-Payload kontrolliert importieren
- `BaseEffect`-Klasse laden
- registrierbare Runtime-Objekte zurueckgeben

`effect_package_builder.py`

- Entwicklungsformat einlesen
- ZIP-Artefakt bauen
- Hashes berechnen
- Signaturmaterial vorbereiten oder erzeugen

`effect_command_registry.py`

- Aliasbefehle pro `source_id` speichern
- Lookup fuer `invoke-command`
- Konflikte und Namespaces pruefen

`effect_source_store.py`

- registrierte Quellen im App-State persistent speichern
- Service-Start-Recovery ermoeglichen

## 6.3 Erweiterung von `EffectRegistry`

`src/effect_registry.py` ist der zentrale Integrationspunkt.

Die Registry soll kuenftig drei Quellarten beherrschen:

1. manuell registrierte Effektklassen
2. dateibasierte Python-Library-Pfade
3. Effektpakete und Effektsets

### Neue Source-Arten

`EffectLibrarySource` sollte zu einer allgemeineren Source-Beschreibung weiterentwickelt werden, zum Beispiel:

- `kind="library_path"`
- `kind="effect_package"`
- `kind="effect_set"`

Zusaetzliche Felder:

- `origin_path`
- `source_id`
- `enabled`
- `release_mode`
- `trust_status`
- `fingerprint`

### Neue Registry-Methoden

Vorgeschlagene Erweiterungen:

- `register_effect_package(path, *, enabled=True, release_mode=False, source_id=None)`
- `register_effect_set(path, *, enabled=True, release_mode=False, source_id=None)`
- `remove_source(source_id)`
- `list_effect_sources()`
- `list_effect_commands()`
- `invoke_command(command_name, *, params=None, target_layer=None, source_id=None)`

### Interne Registry-Datenstruktur

`RegisteredEffectType` sollte erweitert werden um:

- `qualified_effect_id`
- `local_effect_id`
- `source_kind`
- `origin_path`
- `package_id`
- `package_version`

Lookup sollte kuenftig moeglich sein ueber:

- `qualified_effect_id`
- fuer Builtins optional weiterhin ueber bare `effect_id`

Damit bleibt Abwaertskompatibilitaet fuer bestehende Builtins erhalten, waehrend neue Paketquellen sauber namespaced arbeiten.

## 6.4 Runtime-Auswirkung

Die Rendering- und Invocation-Logik in `src/runtime.py` muss nicht neu erfunden werden.

Sie soll weiterhin mit registrierten Effekten arbeiten.

Noetige Anpassungen:

- `apply_effect(...)` muss qualifizierte Effekt-IDs akzeptieren
- Status- und Snapshot-Ausgaben sollen `effect_id` und `qualified_effect_id` zurueckgeben
- Background-State-Persistenz muss qualifizierte IDs sicher speichern koennen

Wichtig:

Die Runtime selbst muss keine ZIP-Dateien verstehen.

Das Laden und Uebersetzen bleibt vor der Runtime in Registry- und Loader-Schicht.

## 6.5 Service-Integration

`src/service.py` bekommt neue Service-Methoden fuer Source-Verwaltung und Befehlsaufruf.

Vorgeschlagene neue Methoden:

- `register_effect_package(...)`
- `register_effect_set(...)`
- `remove_effect_source(source_id)`
- `list_effect_sources()`
- `list_effect_commands(source_id=None)`
- `invoke_effect_command(command_name, payload=None, source_id=None, replace_existing=True)`
- `reload_effect_sources()`

### Service-Start

Beim Start soll der Service zusaetzlich zu `background_state.json` auch eine persistierte Effektquellenliste laden, zum Beispiel aus:

- `runtime_state/effect_sources.json`

Dadurch bleiben bewusst registrierte Pakete und Sets nach Neustarts erhalten.

## 6.6 API-Integration

Die bestehende API unter `src/api.py` wird erweitert.

### Neue Read-Routen

- `GET /api/v1/effect-sources`
- `GET /api/v1/effect-commands`
- `GET /api/v1/effect-commands/{command_name}`

### Neue Write-Routen

- `POST /api/v1/effect-sources/register-package`
- `POST /api/v1/effect-sources/register-set`
- `POST /api/v1/effect-sources/reload`
- `DELETE /api/v1/effect-sources/{source_id}`
- `POST /api/v1/effect-commands/invoke`

### Request-Modelle

Neue Pydantic-Modelle in `src/api.py`:

- `RegisterEffectPackageRequest`
- `RegisterEffectSetRequest`
- `InvokeEffectCommandRequest`

Beispiel fuer Paketregistrierung:

```json
{
  "path": "C:/apps/voice_assistant/effects/voice_assistant.lefxset",
  "enabled": true,
  "release_mode": true
}
```

Beispiel fuer Befehlsaufruf:

```json
{
  "command_name": "listening",
  "source_id": "app.voice_assistant",
  "payload": {
    "color": "#55CCFF"
  },
  "replace_existing": true
}
```

## 6.7 CLI-Integration

Die bestehende Runtime-CLI in `src/cli.py` bleibt die Service-CLI.

Sie wird fuer Registrierung und Befehlsaufruf erweitert, aber Packaging selbst wandert in eine separate Build-CLI.

### Neue Service-CLI-Kommandos

- `list-effect-sources`
- `register-effect-package <file>`
- `register-effect-set <file>`
- `remove-effect-source <source_id>`
- `reload-effect-sources`
- `list-effect-commands`
- `invoke-effect-command <command_name>`

### Neue Packaging-CLI

Empfohlener Einstieg:

- `python .\main.py package ...` ist nicht ideal
- besser: eigenes Tool, zum Beispiel `python .\tools\effect_packager.py ...`

Vorgeschlagene Packaging-Kommandos:

- `pack-effect <src_dir> <out.lefx>`
- `pack-effect-set <src_dir> <out.lefxset>`
- `inspect-effect-package <file>`
- `verify-effect-package <file>`
- `extract-effect-package <file> <target_dir>`
- `sign-effect-package <file>`

## 6.8 Discovery- und Persistenzmodell

Das heutige dateibasierte Builtin-Discovery aus `led_effects/effects/` bleibt bestehen.

Neu kommt ein zweites Discovery-Modell hinzu:

- explizit registrierte Effektquellen

Diese werden nicht implizit von beliebigen Ordnern gescannt, sondern bewusst registriert und im `effect_source_store` persistiert.

Empfohlene Persistenzdatei:

```text
runtime_state/effect_sources.json
```

Inhalt:

- registrierte `source_id`
- `kind`
- `origin_path`
- `enabled`
- `release_mode`
- `registered_at`
- optional `fingerprint`

## 7. API- und CLI-Entwurf im Ueberblick

## 7.1 API-Ueberblick

### Effektquellen

- `GET /api/v1/effect-sources`
- `POST /api/v1/effect-sources/register-package`
- `POST /api/v1/effect-sources/register-set`
- `POST /api/v1/effect-sources/reload`
- `DELETE /api/v1/effect-sources/{source_id}`

### Effektbefehle

- `GET /api/v1/effect-commands`
- `GET /api/v1/effect-commands/{command_name}`
- `POST /api/v1/effect-commands/invoke`

### Effekte

Die bestehende Route `GET /api/v1/effects` bleibt erhalten, liefert aber erweitert:

- `id`
- `qualified_id`
- `source_id`
- `source_kind`
- `package_id`
- `package_version`

## 7.2 CLI-Ueberblick

### Registry und Sources

- `python .\main.py list-effect-sources`
- `python .\main.py register-effect-package .\dist\warn.lefx`
- `python .\main.py register-effect-set .\dist\voice_app.lefxset`
- `python .\main.py remove-effect-source app.voice_assistant`
- `python .\main.py reload-effect-sources`

### Commands

- `python .\main.py list-effect-commands`
- `python .\main.py invoke-effect-command listening --source app.voice_assistant --payload '{"color":"#55CCFF"}'`

### Packaging

- `python .\tools\effect_packager.py pack-effect .\examples\listening .\dist\listening.lefx`
- `python .\tools\effect_packager.py pack-effect-set .\examples\voice_app .\dist\voice_app.lefxset`
- `python .\tools\effect_packager.py verify-effect-package .\dist\voice_app.lefxset`

## 8. Sicherheits- und Betriebsmodell

## 8.1 Vertrauensannahme

Da Python-Code in Paketen ausfuehrbar bleibt, ist das System kein Untrusted-Plugin-System.

Das Sicherheitsmodell lautet daher:

- Paketquellen muessen im Release-Betrieb vertrauenswuerdig sein
- Signaturen sichern Herkunft und Unveraendertheit
- Der Service fuehrt Code weiterhin mit seinen normalen Rechten aus

## 8.2 Release-Regeln

Im Release-Modus gilt:

- nur signierte `.lefx` und `.lefxset`
- Signierer muss im Trust Store freigegeben sein
- freie Ordner-Discovery ausserhalb `led_effects/effects/` ist gesperrt
- `extract-effect-package` ist nur Debug-Werkzeug

## 8.3 Debug-Regeln

Im Debug-Modus gilt:

- Entwicklungsordner duerfen direkt gepackt oder testweise registriert werden
- Extraktion und Inspektion sind erlaubt
- self-signed oder lokale Testsignaturen koennen zugelassen werden

## 9. Implementierungsplan

Der Implementierungsplan ist so geschnitten, dass jede Phase einzeln testbar und reviewbar ist.

## Phase 1: Paket-Schemata und Offline-Validierung

Ziel:

- formale Schemata und Parser fuer `.lefx` und `.lefxset`

Arbeitspakete:

- `effect_package_schema.py` anlegen
- Manifest- und Set-Manifest-Datamodelle anlegen
- Hashdatei- und Signaturdatei-Modell anlegen
- reine Offline-Validierungsfunktionen bauen

Tests:

- neue Unit-Tests fuer gueltige und ungueltige Manifeste
- Hashdatei-Pruefung mit positiven und negativen Faellen
- Versions- und Pflichtfeldtests

Abnahmekriterium:

- Ein Paket kann offline korrekt als gueltig oder ungueltig klassifiziert werden.

## Phase 2: Loader fuer `.lefx`

Ziel:

- einzelne Effektpakete kontrolliert laden und in registrierbare Effektklassen uebersetzen

Arbeitspakete:

- ZIP-Oeffnung
- `manifest.json`, `hashes.json`, `signature.json` laden
- Python-Payload temporär importieren
- Entry-Klasse pruefen
- Konsistenzcheck zwischen Manifest und `EffectDefinition`

Tests:

- Registry-nahe Loader-Tests mit temporaer erzeugten Paketen
- Fehlerfaelle fuer fehlende Entry-Klasse, inkonsistente IDs, kaputte Hashes

Abnahmekriterium:

- Ein `.lefx` kann isoliert geladen und validiert werden.

## Phase 3: Loader fuer `.lefxset` und Command-Mapping

Ziel:

- Effektsets mit mehreren Effekten und App-Kommandos laden

Arbeitspakete:

- `set-manifest.json` parsern
- enthaltene `.lefx`-Dateien laden
- `commands.json` validieren
- `effect_command_registry.py` aufbauen

Tests:

- Set-Loader-Tests
- Konflikttests fuer doppelte Commands
- Tests fuer Namespace- und `source_id`-Konsistenz

Abnahmekriterium:

- Ein `.lefxset` kann als komplette Quelle geladen werden und stellt valide Commands bereit.

## Phase 4: Integration in `EffectRegistry`

Ziel:

- Paketquellen als echte Registry-Sources integrieren

Arbeitspakete:

- Source-Typen erweitern
- `register_effect_package()` und `register_effect_set()` einfuehren
- qualifizierte IDs unterstuetzen
- Entfernen und Reload von Sources unterstuetzen

Tests:

- Ausbau von `tests/test_effect_registry.py`
- neue Tests fuer Paketquellen, Reload, Remove, Konflikte, Disabled-Sources

Abnahmekriterium:

- Die Registry kann Builtins, Library-Pfade und Paketquellen gleichzeitig sauber verwalten.

## Phase 5: Service, API und CLI erweitern

Ziel:

- Paketregistrierung und Command-Aufruf nach aussen verfuegbar machen

Arbeitspakete:

- Service-Methoden erweitern
- API-Routen und Pydantic-Modelle einfuehren
- CLI-Parser und Client erweitern

Tests:

- Ausbau von `tests/test_api.py`
- Ausbau von `tests/test_cli.py`
- Client-Tests fuer neue Requests

Abnahmekriterium:

- Effektquellen koennen ueber API und CLI registriert, gelistet, entfernt und aufgerufen werden.

## Phase 6: Source-Persistenz und Start-Recovery

Ziel:

- registrierte Quellen ueber Neustarts hinweg erhalten

Arbeitspakete:

- `effect_source_store.py` anlegen
- Persistenzdatei in `runtime_state/` einfuehren
- Service-Start um Source-Recovery erweitern

Tests:

- Service-Tests fuer Wiederherstellung registrierter Quellen
- Fehlerfalltests fuer fehlende oder kaputte Persistenzdatei

Abnahmekriterium:

- Registrierte Paketquellen bleiben nach Service-Neustart vorhanden.

## Phase 7: Packaging-CLI

Ziel:

- Entwicklungsformat in `.lefx` und `.lefxset` ueberfuehren

Arbeitspakete:

- separates Tool unter `tools/`
- `pack-effect`
- `pack-effect-set`
- `inspect`
- `verify`
- optional `extract`

Tests:

- Builder-Tests
- Roundtrip-Tests: Entwicklungsordner -> Paket -> Loader -> Registry

Abnahmekriterium:

- Ein Entwickler kann aus einem lesbaren Quellordner ein lauffaehiges Paket bauen und verifizieren.

## Phase 8: Signatur- und Release-Modus haerten

Ziel:

- produktionsnahe Betriebsregeln aktivieren

Arbeitspakete:

- Signaturpruefung mit Trust Store
- Release-Mode-Flags
- Debug/Release-Verhalten in Loader und CLI trennen

Tests:

- Signaturtests mit gueltigen und ungueltigen Schluesseln
- API- und Service-Tests fuer Release-Abweisung unsignierter Pakete

Abnahmekriterium:

- Release-Betrieb akzeptiert nur vertrauenswuerdige Paketquellen.

## Phase 9: Dokumentation und Beispielpakete

Ziel:

- die neue Funktionalitaet fuer Repo und Nutzer nachvollziehbar machen

Arbeitspakete:

- `docs/effects.md` erweitern
- API-Guides aktualisieren
- Beispielquelle und Beispiel-Set unter `examples/` oder `led_effects/` anlegen

Tests:

- Dokumentationsbeispiele gegen reale CLI/API pruefen

Abnahmekriterium:

- Das System ist nicht nur implementiert, sondern auch benutzbar dokumentiert.

## 10. Teststrategie fuer die Gesamtumsetzung

Zur Umsetzung gehoert explizit eine durchgehende Verifikation.

Die Teststrategie sollte folgende Ebenen enthalten:

### Unit-Tests

- Manifest-Parser
- Hash- und Signaturpruefung
- Loader fuer `.lefx`
- Loader fuer `.lefxset`
- Command-Registry

### Integrations-Tests

- Registry mit Builtins plus Paketquellen
- API-Registrierung und API-Aufruf von Befehlen
- CLI-Parser und Client-Wege
- Service-Neustart mit wiederhergestellten Quellen

### End-to-End-nahe Tests

- Entwicklungsordner packen
- Paket verifizieren
- Paket registrieren
- Command ueber CLI oder API invoke
- erwarteten Effektstatus im Runtime-Snapshot pruefen

### Bestehende Test-Suites, die mitlaufen muessen

- `tests/test_effect_registry.py`
- `tests/test_api.py`
- `tests/test_cli.py`
- `tests/test_runtime.py`
- `tests/test_service.py`
- idealerweise gesamtes `pytest -q`

## 11. Empfohlene Reihenfolge fuer die spaetere Umsetzung

Die sinnvollste Umsetzungsreihenfolge ist:

1. Schema und Loader
2. `.lefx`
3. `.lefxset`
4. Registry-Integration
5. Service/API/CLI
6. Persistenz
7. Packaging-CLI
8. Signaturen haerten
9. Doku und Beispiele

So bleibt die Runtime waehrend der Einfuehrung stabil, und jede Stufe ist separat testbar.

## 12. Zusammenfassung des finalen Zielmodells

Das finale Zielmodell dieses Branches lautet:

- Die bestehende Python-Runtime bleibt erhalten.
- Ein einzelner Effekt wird als `.lefx` ausgeliefert.
- Eine anwendungsnahe Effektbibliothek wird als `.lefxset` ausgeliefert.
- Effektpakete duerfen Python-Logik enthalten.
- Integritaet und Herkunft werden ueber Hashes und Signaturen abgesichert.
- Registrierung und Discovery laufen source-basiert ueber die Registry.
- Anwendungen sprechen vorzugsweise ueber Command-Aliasse statt rohe Effekt-IDs.
- Debug- und Release-Betrieb werden sauber getrennt.
- Packaging wird ueber ein separates Build-Werkzeug realisiert.

Damit entsteht kein Ersatz der heutigen Effekt-Engine, sondern eine stabile Distributions- und Integrationsschicht ueber dem bereits vorhandenen System.

## 13. Offene Entscheidungen fuer das Gruene Licht

Das Konzept ist weitgehend entscheidungsreif. Fuer die spaetere Implementierung waeren nur noch diese kompakten Restentscheidungen hilfreich:

1. Soll Signaturpruefung direkt in der ersten technischen Umsetzung verpflichtend sein, oder duerfen wir zuerst mit Hash-Pruefung plus optionaler Signatur beginnen und die strikte Release-Pruefung danach haerten?
2. Soll `qualified_effect_id` nach dem vorgeschlagenen Schema `source_id::effect_id` eingefuehrt werden, auch wenn dafuer einige Status- und Persistenzfelder erweitert werden muessen?
3. Sollen registrierte Effektquellen ueber Neustarts hinweg standardmaessig persistiert werden, oder nur optional per Flag?
4. Soll die erste Packaging-CLI direkt Signieren unterstuetzen oder zuerst nur `pack`, `inspect` und `verify`?
5. Soll fuer Debug-Zwecke zusaetzlich auch die Registrierung lesbarer Entwicklungsordner vorgesehen werden, oder wollen wir experimentell von Anfang an nur mit `.lefx` und `.lefxset` arbeiten?

Wenn diese Punkte bestaetigt sind, ist der naechste Schritt keine weitere Konzeptphase mehr, sondern die konkrete Implementierung entlang des obigen Plans.
