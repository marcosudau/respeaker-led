# Folgekonzept: Parametrisierbare Effekte, Effect-Presets und feste Commands

Stand: 2026-04-12
Status: Entscheidungsreifes Zielkonzept fuer die naechste Ausbaustufe

## 1. Ausgangsfrage

Die offene Kernfrage ist:

Wie ueberfuehren wir die bestehenden parametrisierbaren Standardeffekte in das neue LEFX-/LEFXSET-Modell, obwohl die neuen Commands bewusst feste, payload-freie Bedienpunkte sind
und damit gerade nicht fuer freie Parameteruebergabe gedacht sind?

Meine klare Antwort darauf ist:

Wir sollten dieses Problem nicht dadurch loesen, dass wir Commands wieder aufweichen.

Stattdessen sollten wir die Ebenen sauber trennen:

1. `Effect`
2. `Effect Preset`
3. `Command`

Genau diese Trennung macht das Modell langfristig sauber, erklaerbar und technisch wartbar.

## 2. Kernentscheidung

## 2.1 Empfohlene Modelltrennung

### Ebene A: Effect

Der Effekt ist die eigentliche, parametrisierbare Render-Einheit.

Er enthaelt:

- Renderlogik
- `parameter_schema`
- Defaults
- Layer-Regeln
- Capabilities

Er bleibt frei parametrisierbar.

Beispiel:

- `default-effects::soft_pulse`
- `default-effects::warning_flash`
- `default-effects::timer_ring`

### Ebene B: Effect Preset

Ein Effect Preset ist eine benannte, stabile Vorkonfiguration eines Effekts.

Ein Preset legt typischerweise fest:

- welcher Effekt verwendet wird
- auf welchem Layer er angewendet wird
- welche Parameter gesetzt werden
- optional Dauer, Queueing oder andere Aufrufoptionen

Beispiel:

- `default-effects::idle_soft_blue`
- `default-effects::error_flash_red_fast`
- `default-effects::timeout_ring_orange`

Ein Preset ist damit die Bruecke zwischen frei parametrisierbaren Effekten und stabilen, leicht konsumierbaren Bedienpunkten.

### Ebene C: Command

Ein Command bleibt ein fester, payload-freier Bedienpunkt.

Commands sind gedacht fuer:

- API-Integrationen
- CLI-Shortcuts
- Buttons
- Automationen
- Voice-Trigger
- fest verdrahtete App-Integrationen

Ein Command referenziert also kuenftig bevorzugt ein Preset, nicht direkt freie Parameter.

## 2.2 Warum das besser ist als parametrisierte Commands

Wenn wir Commands wieder mit beliebigen Params oeffnen, verlieren wir genau den Vorteil, den wir mit dem neuen Command-Modell gerade gewonnen haben:

- stabile Schnittstellen
- klare Integrationspunkte
- einfache Testbarkeit
- einfache Dokumentierbarkeit
- keine App-spezifischen Payload-Vertraege in `commands.json`

Deshalb mein klares Votum:

- Effekte bleiben parametrisierbar
- Presets kapseln sinnvolle benannte Parameterauspraegungen
- Commands bleiben feste Trigger

## 3. Einordnung in die bestehende Architektur

Heute gibt es im Projekt bereits drei relevante Konzepte:

1. `EffectRegistry`
   Registriert Effekte aus Builtins, `.lefx` und `.lefxset`.

2. `EffectCommandRegistry`
   Registriert die festen effect commands aus `.lefxset`.

3. `PresetRegistry`
   Das ist das heutige, aeltere Preset-System fuer Preset-Packs unter `preset.yaml`/`preset.py`.

Die wichtige Beobachtung ist:

Der Begriff `Preset` existiert schon, meint aber heute nicht dasselbe wie das hier vorgeschlagene paketbasierte Effekt-Preset.

Deshalb sollten wir diese neue Ebene im naechsten Schritt bewusst als `effect preset` fuehren und nicht einfach das Wort `preset` ungequalifiziert wiederverwenden.

Meine Empfehlung fuer die Benennung:

- neues Paket-/Registry-Konzept: `effect preset`
- heutiges bestehendes Preset-System intern weiter als `legacy preset` oder `scene preset` behandeln

So vermeiden wir Begriffskollisionen.

## 4. Das Zielmodell im Detail

## 4.1 Effect

Der Effect bleibt unveraendert die kleinste parametrisierbare Runtime-Einheit.

Wichtige Eigenschaften:

- bleibt als `.lefx` distributierbar
- bleibt direkt per `apply_effect(...)` aufrufbar
- bleibt fuer Power-User und interne dynamische Calls frei parametrisierbar

Das bedeutet:

Standardeffekte muessen nicht entparametrisiert werden.

Sie werden einfach als First-Party-`.lefx` modelliert und behalten ihre Parameterfaehigkeit vollstaendig.

## 4.2 Effect Preset

Das Effect Preset ist eine neue, klar definierte Schicht ueber dem Effect.

Ein Preset soll diese Fragen beantworten:

- welchen Effekt nutze ich
- auf welchem Layer
- mit welchen festen Parametern
- mit welchen optionalen Aufrufoptionen

### Minimales Preset-Datenmodell

Ein Preset sollte mindestens enthalten:

- `preset_id`
- `effect`
- `target_layer`
- `params`

Optional:

- `title`
- `description`
- `duration_ms`
- `priority`
- `enqueue`
- `replace_existing`
- `tags`

### Empfohlene Identitaet

Symmetrisch zum Effect-Modell:

- `qualified_effect_id = source_id::effect_id`
- `qualified_preset_id = source_id::preset_id`

Innerhalb einer Set-Quelle duerfen Presets lokale IDs benutzen.
Nach aussen sollten sie qualifiziert dargestellt werden.

## 4.3 Command

Commands bleiben absichtlich einfach.

Empfohlenes Zielverhalten:

- `state_toggle` referenziert fuer `on` bevorzugt ein Preset
- `off` bleibt meist `clear_layer`
- `event` referenziert fuer `on` bevorzugt ein Preset
- direkte Effekt-Referenzen in Commands bleiben in einer Uebergangsphase zulaessig, aber nicht mehr der bevorzugte First-Party-Stil

## 5. Empfohlenes Dateimodell

## 5.1 Kein neues Standalone-Dateiformat in der ersten Ausbaustufe

Ich wuerde fuer die erste Ausbaustufe bewusst **kein** neues eigenstaendiges Paketformat wie `.lefxpreset` einfuehren.

Das waere im Moment zu viel Mechanik fuer zu wenig echten Nutzen.

Mein bevorzugter Kurs:

Effect Presets werden zunaechst als Teil eines `.lefxset` modelliert.

Also:

- `.lefx` fuer einzelne parametrisierbare Effekte
- `.lefxset` fuer eine Quelle mit Effekten, Presets und optional Commands

Das ist einfach, source-zentriert und passt gut zum bestehenden Source-Modell.

## 5.2 Empfohlene Set-Struktur

Ich wuerde das Set-Modell um eine optionale Datei `effect-presets.yaml` erweitern.

Empfohlene Struktur:

```text
my_source/
  set.yaml
  effect-presets.yaml
  commands.json
  effects/
    soft_pulse.lefx
    warning_flash.lefx
    timer_ring.lefx
```

`effect-presets.yaml` ist dabei die primaere menschenfreundliche Variante.
Optional kann spaeter auch `effect-presets.json` zulaessig sein.

## 5.3 Beispiel fuer `effect-presets.yaml`

```yaml
presets:
  idle_soft_blue:
    title: Idle Soft Blue
    description: Ruhiger blauer Idle-Preset fuer den State-Layer.
    effect: default-effects::soft_pulse
    target_layer: STATE_LAYER
    params:
      color: "#33AAFF"
      base_color: "#050A0F"
      period_ms: 1800
    tags:
      - state
      - idle

  error_flash_red_fast:
    title: Error Flash Red Fast
    effect: default-effects::warning_flash
    target_layer: EVENT_LAYER
    duration_ms: 450
    params:
      color: "#FF3B30"
      period_ms: 220
    tags:
      - event
      - error
```

## 5.4 Beispiel fuer `commands.json`

```json
{
  "commands": {
    "idle": {
      "kind": "state_toggle",
      "on": {
        "preset": "idle_soft_blue"
      },
      "off": {
        "action": "clear_layer",
        "target_layer": "STATE_LAYER"
      }
    },
    "error_flash": {
      "kind": "event",
      "on": {
        "preset": "error_flash_red_fast"
      }
    }
  }
}
```

Wichtig:

In `commands.json` sollte der Bezug auf ein Preset source-lokal moeglich sein.
Beim Laden wird daraus intern ein qualifizierter Bezug.

## 6. API- und Runtime-Modell

## 6.1 Grundsatz

Es soll kuenftig drei Nutzungswege geben.

### Weg A: Direkter parametrisierter Effect-Call

Das bleibt fuer flexible Aufrufe bestehen.

Beispiel:

- `POST /api/v1/commands/apply_effect`

Das ist der Low-Level- oder Power-User-Pfad.

### Weg B: Effect Preset anwenden

Das ist der benannte, aber noch parametrierte Mittelweg.

Empfohlene neue Endpunkte:

- `GET /api/v1/effect-presets`
- `GET /api/v1/effect-presets/{source_id}`
- `GET /api/v1/effect-presets/{source_id}/{preset_id}`
- `POST /api/v1/effect-presets/{source_id}/{preset_id}/apply`

Dieser Pfad ist ideal fuer:

- UI-Kataloge
- einfache App-Auswahl
- kuratierte Standardvarianten
- spaetere Preset-Galerien

### Weg C: Fester Command

Das bleibt der payload-freie Integrationspfad.

Bestehende Form:

- `POST /api/v1/commands/{source_id}/{command_name}`
- `POST /api/v1/commands/{source_id}/{command_name}/on`
- `POST /api/v1/commands/{source_id}/{command_name}/off`

## 6.2 Empfohlene Registry-Struktur

Ich wuerde die Runtime um eine eigene `EffectPresetRegistry` ergaenzen.

Zielbild:

- `EffectRegistry`
- `EffectPresetRegistry`
- `EffectCommandRegistry`

Beziehungen:

- Presets referenzieren Effekte
- Commands referenzieren bevorzugt Presets

Das ergibt eine klare Richtung:

`Command -> Preset -> Effect`

Der direkte Pfad `Command -> Effect` bleibt fuer Bestand und Uebergang zunaechst moeglich, ist aber nicht mehr die bevorzugte Zielrichtung.

## 6.3 Aufrufsemantik

Wenn ein Preset angewendet wird, wird intern ein normaler `apply_effect(...)`-Aufruf daraus erzeugt.

Das Preset ist also keine neue Render-Einheit, sondern nur ein kuratierter Invocation-Wrapper.

Das ist wichtig, weil:

- keine doppelte Runtime-Logik entsteht
- Tests auf der bestehenden Invocation-Schicht aufbauen koennen
- die Capabilities und Layer-Regeln weiter am Effekt haengen

## 7. Validierung

Das Modell ist nur dann wirklich sauber, wenn Presets streng validiert werden.

Ich wuerde diese Regeln hart erzwingen.

## 7.1 Referenzvalidierung

- referenzierter Effekt existiert
- Effekt gehoert zur erwarteten Quelle
- `qualified_preset_id` ist eindeutig

## 7.2 Parameter-Validierung

- alle gesetzten Params existieren im `parameter_schema`
- Typen passen
- Mindest-/Hoechstwerte passen
- Enum-Werte passen

## 7.3 Layer-Validierung

- `target_layer` ist fuer den Effekt erlaubt
- Playback-/Duration-Regeln des Effekts werden eingehalten

## 7.4 Command-Validierung

- referenziertes Preset existiert
- ein Toggle-Command mit `on.preset` und `off.clear_layer` bleibt semantisch konsistent
- Event-Commands verweisen nicht auf ungueltige Presets oder ungueltige Layer

## 8. Umgang mit dem bestehenden Preset-System

## 8.1 Problem

Heute gibt es bereits `PresetRegistry` und Preset-Packs mit `preset.yaml` und `preset.py`.

Diese sind fachlich nicht identisch mit den hier vorgeschlagenen paketbasierten Effect Presets.

Wenn wir beides vermischen, entsteht schnell Begriffschaos.

## 8.2 Empfohlener Umgang

Ich wuerde das **nicht** in derselben Umsetzung sofort zusammenziehen.

Empfohlener Kurs:

1. Das neue paketbasierte `effect preset` als eigenes Konzept einfuehren.
2. Das heutige Preset-System vorerst unveraendert lassen.
3. Spaeter separat entscheiden, ob das alte Preset-System:
   - migriert,
   - umbenannt,
   - oder als hoeherstufiges Spezialkonzept bestehen bleibt.

## 8.3 Begriffsregel fuer die naechste Stufe

Damit es sauber bleibt, wuerde ich sprachlich ab jetzt unterscheiden:

- `effect preset`
- `legacy preset`

Nicht einfach nur:

- `preset`

## 9. Konkrete Konsequenz fuer die Ueberfuehrung der Standardeffekte

Mit diesem Modell wird die offene Parameterfrage sauber geloest.

Die Standardeffekte werden dann kuenftig so abgebildet:

### Schritt 1

Jeder Builtin-Effekt wird als First-Party-`.lefx` modelliert.

Beispiele:

- `default-effects::soft_pulse`
- `default-effects::solid_color`
- `default-effects::warning_flash`
- `default-effects::timer_ring`

### Schritt 2

Fuer haeufige Standardvarianten werden First-Party-Effect-Presets angelegt.

Beispiele:

- `default-effects::idle_soft_blue`
- `default-effects::listening_pulse_cyan`
- `default-effects::error_flash_red_fast`
- `default-effects::timeout_ring_orange`

### Schritt 3

Nur wo wirklich feste Integrationspunkte gebraucht werden, kommen Commands dazu.

Beispiele:

- `idle`
- `listening`
- `error_flash`
- `timeout_warning`

Damit muessen nicht alle Builtins Commands bekommen.

Das ist wichtig.

Denn:

- nicht jeder Effekt braucht einen festen Trigger
- manche Effekte sind eher Material fuer Presets oder direkte API-Nutzung
- das Command-Modell bleibt dadurch klein und stabil

## 10. Mein bevorzugter Implementierungsplan

Ich wuerde diese Ausbaustufe in vier Phasen schneiden.

## Phase A: Datenmodell und Loader

- neues `EffectPresetManifest`
- neuer `EffectPresetRegistry`
- Loader fuer `effect-presets.yaml` oder `effect-presets.json`
- Validierung gegen registrierte Effekte

## Phase B: Runtime und Service

- `list_effect_presets()`
- `effect_preset_info(...)`
- `apply_effect_preset(...)`
- API- und CLI-Endpunkte dafuer

## Phase C: Commands auf Presets erweitern

- `commands.json` darf `preset` statt `effect` referenzieren
- interne Aufloesung zu `apply_effect(...)`
- bestehende direkte Effekt-Commands bleiben kompatibel

## Phase D: First-Party-Builtins migrieren

- erste First-Party-Effect-Quelle fuer Builtins
- kuratierte Effect-Presets definieren
- nur ausgewaehlte Commands darauf aufsetzen

## 11. Die drei Entscheidungen, die ich dir jetzt konkret empfehlen wuerde

Damit wir danach direkt in die Umsetzung gehen koennen, wuerde ich diese drei Punkte jetzt als Zielentscheidungen festziehen.

### Entscheidung 1: Presets als Teil von `.lefxset`, nicht als neues eigenes Paketformat

Meine Empfehlung:

- ja

Grund:

- einfacher
- source-zentriert
- weniger neue Mechanik
- fuer den aktuellen Bedarf vollkommen ausreichend

### Entscheidung 2: Commands bleiben payload-frei und referenzieren bevorzugt Presets

Meine Empfehlung:

- ja

Grund:

- erhaelt die neue klare Integrationsgrenze
- verhindert schleichende Rueckkehr zu app-spezifischen Command-Payloads

### Entscheidung 3: Der erste API-/CLI-Stand fuer Presets erlaubt keine Laufzeit-Overrides

Meine Empfehlung:

- ja

Also:

- `apply_effect_preset(...)` nutzt exakt das definierte Preset
- keine ad-hoc Param-Overrides in V1 der Preset-Schicht

Grund:

- das Modell bleibt klar
- Validierung bleibt einfach
- Presets bleiben wirklich stabile, benannte Invocationen

Wenn spaeter Bedarf fuer leichte Overrides entsteht, kann das als bewusste zweite Stufe kommen.

## 12. Mein Schlussfazit

Die Parameterfrage ist aus meiner Sicht kein Hindernis fuer die Vereinheitlichung der Standardeffekte.

Sie zeigt nur, dass wir zwischen drei Dingen sauber unterscheiden muessen:

- dem parametrisierbaren Effekt
- dem benannten Preset
- dem festen Command

Mein bevorzugtes Zielbild ist deshalb:

`Effect -> frei parametrisierbar`

`Effect Preset -> benannte, feste Parameterauspraegung`

`Command -> payload-freier Trigger auf Preset oder im Uebergang direkt auf Effekt`

Damit behalten wir die Staerken beider Seiten:

- die Ausdruckskraft der bisherigen parametrisierbaren Builtins
- und die Stabilitaet des neuen festen Command-Modells

## 13. Meine klare Umsetzungsempfehlung

Wenn du mir dafuer gruens Licht gibst, wuerde ich die naechste Implementierungsstufe genau auf diesem Kurs bauen:

1. `effect-presets.yaml` als neuer optionaler Teil von `.lefxset`
2. neue `EffectPresetRegistry`
3. neue API-/CLI-Endpunkte fuer `list/info/apply`
4. Commands duerfen Presets referenzieren
5. erst danach schrittweise First-Party-Migration der Standardeffekte

Das waere aus meiner Sicht die sauberste und risikoaermste Fortsetzung.
