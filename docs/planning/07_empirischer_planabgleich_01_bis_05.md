# Empirischer Planabgleich 01 bis 05

Stand: 2026-04-09

Hinweis:

Dieser Bericht beschreibt den Stand vor der spaeteren Auslagerung der konkreten Effektklassen in `src/led_effects/effects/`.
Die hier genannten frueheren Dateipfade fuer Effektimplementierungen in `src/` sind deshalb heute nur noch historisch zu lesen.

## Zweck dieses Berichts

Dieser Bericht gleicht die urspruenglichen Planungsunterlagen 01 bis 05 aus `docs/planning/` mit dem heute real erreichten Zustand des umgebauten Service-Kerns ab.

Geprueft wurde dabei nicht nur die Dokumentation, sondern vor allem die tatsaechliche Implementierung in `src/` sowie die aktuell gruene Testsuite.

Die Auswertung bezieht sich auf die in den Planungsdokumenten beschriebene Neuausrichtung des laufenden Controller-Dienstes. Der hier beschriebene Vergleich entstand noch vor der spaeteren Bereinigung des frueher parallel vorhandenen Direkt-Engine-Zweigs.

## Methodik

Fuer den Abgleich wurden herangezogen:

- die Originaldokumente `01_zielarchitektur.md` bis `05_technisches_zielschema.md`
- der aktuelle Service-Kern in `src/`
- die zugehoerigen Architektur-, Registry-, Normalisierungs-, Runtime-, CLI- und API-Tests
- der aktuelle Vollsuite-Stand: `232 passed`

## Gesamtfazit

Die urspruenglichen Planungen wurden in ihrem architektonischen Kern sehr weitgehend getroffen.

Insbesondere als klar erreicht anzusehen sind:

- eine invocation-basierte zentrale Engine fuer den Service-Kern
- das finale Sechs-Layer-Modell mit den geplanten Prioritaeten
- die vorgeschaltete Normalisierungsschicht
- die Trennung von `EffectDefinition`, `EffectInvocation`, `LayerState` und Registry
- die Event-Queue mit `priority + FIFO` ohne Preemption des laufenden Events
- die Migration der frueheren Spezialfaelle `direction`, `countdown` und `progress` in normale Effektklassen
- die Vereinheitlichung der oeffentlichen Eingabepfade auf dieselbe innere Runtime

Nicht vollstaendig ausgebaut sind vor allem drei Randbereiche:

- eine oeffentliche Bedienoberflaeche fuer Registry-Library-Pfade und Reload
- die vollstaendige Preset-Migration weg von Legacy-Visual-Kompatibilitaet hin zu reinem `effect_id`-basiertem Mapping

Wichtig ist dabei: Diese offenen Punkte betreffen vor allem Ausbaugrad und Endkonsolidierung. Das zentrale Zielmodell der neuen Engine ist praktisch erreicht und produktiv im Code verankert.

## 01 Zielarchitektur

### Kernaussagen des Dokuments

Das Dokument 01 verlangt im Wesentlichen:

- genau eine offizielle Ausfuehrungs-Engine
- ein Layer-System als Source of Truth
- eine vorgeschaltete Normalisierungsschicht
- einen festen Datenfluss `NormalizedCommand -> EffectInvocation -> LayerState -> Scene -> Frame -> Adapter`
- keine Runtime-Sonderpfade fuer fachliche Namen oder Spezialfaelle wie `direction`, `countdown`, `progress`
- keine Umgehung der Engine durch CLI, API, Adapter oder Komfort-Einstiege

### Empirischer Befund

Der Kern dieses Zielbilds ist umgesetzt.

Die eine offizielle Service-Engine ist heute `ControllerRuntime` in `src/engine/runtime.py`. Der laufende Dienst `ControllerService` kapselt genau diese Runtime und rendert ueber denselben Pfad fortlaufend in den Adapter. API, CLI-Remote-Pfade und STT-Adapter sprechen nicht eigene Renderpfade an, sondern landen ueber Service oder Runtime wieder in derselben Engine.

Das Layer-System ist tatsaechlich die Source of Truth. `LayerStore` in `src/core/layers.py` haelt die aktuellen `LayerEntry`- und `LayerState`-Objekte, einschliesslich Event-Queue. `SceneComposer` liest ausschliesslich aus diesem Store und baut daraus die Scene. `SceneRenderer` erzeugt daraus den finalen Frame.

Die Normalisierung ist vorgeschaltet. `ControllerCommandNormalizer` in `src/engine/normalization.py` mappt fachliche Befehle wie `set_state`, `emit_event`, `set_direction`, `start_timeout_countdown` und `set_progress` in `NormalizedCommand`. Danach wird ueber `build_effect_invocation(...)` gegen die Registry validiert und in `EffectInvocation` ueberfuehrt.

Der geplante Datenfluss ist damit in der Implementierung tatsaechlich vorhanden:

- Eingabe in CLI, API, Service oder Adapter
- Normalisierung in `src/engine/normalization.py`
- Validierung und Erzeugung einer `EffectInvocation`
- Ablage im `LayerStore`
- Composition in `src/engine/composer.py`
- Rendering in `src/engine/renderer.py`
- Ausgabe ueber den konfigurierten Adapter

Auch die ausdruecklich genannten Spezialfaelle wurden aus der Runtime herausgezogen. `direction_indicator`, `countdown_ring` und `progress_bar` leben heute als normale Effektklassen in der dateibasierten Effektbibliothek unter `src/led_effects/effects/`; die Runtime behandelt sie nicht mehr als eigene Render-Sonderpfade.

### Bewertung

Bewertung: ueberwiegend bis weitgehend erfuellt.

Die Zielarchitektur ist im Service-Kern heute real vorhanden. Eine kleine Einschraenkung bleibt bei den Presets: Diese liefern teilweise noch Legacy-Visuals und werden ueber die Kompatibilitaetshuellen `legacy_visual`, `set_state_visual(...)` und `set_active_visual(...)` eingebracht. Das umgeht die Engine nicht, ist aber noch nicht die strengste denkbare Endform des Zielbildes.

## 02 Effektdefinition und Registry

### Kernaussagen des Dokuments

Das Dokument 02 fordert:

- eine Python-Effektklasse als registrierbare Grundeinheit
- `EffectDefinition` und Renderlogik logisch an derselben Klasse
- intern weiterhin klare Trennung von Definition, Invocation und Registry
- keine Effekte als JSON mit eingebettetem Python-Code
- Built-ins plus optionale zusaetzliche Library-Pfade
- expliziten Reload
- Discovery ueber Python-Module und `BaseEffect`-Subklassen
- saubere Validierung und Duplicate-ID-Fehler

### Empirischer Befund

Diese Struktur ist heute implementiert.

`src/core/effect_schema.py` enthaelt die Basistypen `EffectDefinition`, `EffectInvocation`, `EffectParamDefinition`, `EffectCapabilities`, `LayerRule`, `RenderContext` und `BaseEffect`. Die konkreten Effektklassen leben heute dateibasiert unter `src/led_effects/effects/`, tragen ihre `definition` als Klassenattribut und implementieren `render(ctx)` direkt an derselben Klasse.

Die Registry in `src/engine/effect_registry.py` bildet das in Dokument 02 beschriebene Modell praktisch nach:

- `RegisteredEffectType`
- `EffectLibrarySource`
- `EffectRegistry.register(...)`
- `EffectRegistry.add_library_path(...)`
- `EffectRegistry.reload()`
- Discovery ueber Python-Module und `BaseEffect`-Subklassen
- Duplicate-ID-Pruefung
- Validierung von IDs, Titel, Beschreibung, Parameter-Schema und Layer-Regeln

Die Tests in `tests/test_effect_registry.py` bestaetigen diese Punkte empirisch:

- Registrierung von Effektklassen
- Duplicate-ID-Fehler
- ungultige IDs
- Discovery aus Testbibliotheken
- expliziter Reload
- deaktivierte Library-Sources werden nicht geladen

### Abweichungen und Nuancen

Zwei Nuancen weichen von der woertlichen Planungsform ab:

1. Built-ins werden heute nicht aus einem festen Built-in-Verzeichnis discovered, sondern explizit ueber `BUILTIN_EFFECT_CLASSES` zentral registriert. Funktional erfuellt das denselben Zweck, ist sogar reproduzierbarer, entspricht aber nicht der woertlichen Discovery-Idee.

2. Die Library-Pfad-Verwaltung existiert programmatisch in der Registry, ist aber noch nicht als oeffentliche CLI- oder API-Bedienflaeche verfuegbar. Die in Dokument 02 als spaetere Zielkommandos skizzierten Verwaltungsbefehle existieren derzeit nicht.

### Bewertung

Bewertung: weitgehend erfuellt.

Das Effekt- und Registry-Modell wurde sehr nah an der Planung umgesetzt. Offen ist vor allem die oeffentliche Bedienbarkeit der Library-Verwaltung; der Kernmechanismus selbst ist vorhanden und getestet.

## 03 Umbauplan

### Kernaussagen des Dokuments

Dokument 03 beschreibt die Phasenfolge:

1. Zielmodell festziehen
2. Registry und Effektdefinition
3. Normalisierungsschicht
4. Runtime auf neues Layermodell
5. Effekte migrieren
6. Oeffentliche Einstiege umstellen
7. Bereinigung und Abschluss

### Empirischer Befund je Phase

**Phase 1: Zielmodell festziehen**

Erreicht. Die finalen Layer, Prioritaeten, Kern-Datentypen und Queue-Regeln stehen produktiv in `src/core/effect_schema.py`, `src/core/layers.py` und `src/engine/normalization.py`.

**Phase 2: Registry und Effektdefinition**

Erreicht. `src/engine/effect_registry.py` und die dateibasierte Effektbibliothek unter `src/led_effects/effects/` bilden die geplanten Bausteine ab. Das ist durch `tests/test_effect_registry.py` und `tests/test_builtin_effects.py` abgesichert.

**Phase 3: Normalisierungsschicht**

Erreicht. `src/engine/normalization.py` ist genau die vorgesehene Schicht. `tests/test_normalization.py` prueft die Mapping-Pfade fuer State, Clear, Event und Direction.

**Phase 4: Runtime auf neues Layermodell**

Erreicht. `src/engine/runtime.py`, `src/core/layers.py` und `src/engine/composer.py` arbeiten auf Basis von `LayerState` und `EffectInvocation` statt auf dem alten direkten Visual-Zustand.

**Phase 5: Effekte migrieren**

Erreicht. Die frueheren Spezialfaelle sind heute normale Effektklassen in `src/led_effects/effects/`. Das gilt fuer Progress, Direction und Countdown.

**Phase 6: Oeffentliche Einstiege umstellen**

Weitgehend erreicht. `src/interfaces/cli.py`, `src/interfaces/api.py`, `src/services/service.py`, `src/interfaces/client.py` und `src/integrations/stt_adapter.py` greifen nicht auf separate Render-Parallelwelten zu, sondern landen auf derselben Runtime. Die Tests `tests/test_cli.py`, `tests/test_api.py`, `tests/test_client.py`, `tests/test_service.py` und `tests/test_stt_adapter.py` decken diese Ebene ab.

**Phase 7: Bereinigung und Abschluss**

Ueberwiegend erreicht. `tests/test_architecture.py` prueft, dass zentrale Legacy-Marker aus `src/` entfernt wurden. Die Vollsuite ist aktuell gruen. Was noch sichtbar bleibt, sind bewusst belassene Kompatibilitaetspfade fuer Legacy-Visuals und Presets.

### Bewertung

Bewertung: erfuellt.

Der in Dokument 03 beschriebene Umbaupfad ist nicht nur formal dokumentiert, sondern im Code praktisch durchlaufen worden. Gegenueber dem im Planlog genannten damaligen Stand `221 passed` ist der aktuelle empirische Stand sogar hoeher: `232 passed`.

## 04 Entscheidungen

### Kernaussagen des Dokuments

Dokument 04 fixiert die Architekturentscheidungen zu:

- Trennung von Definition und Invocation
- engine-gezogenem Rendering
- finalen Layernamen
- Dauer in Millisekunden
- Prioritaetsmodell
- Persistenz nur fuer `BACKGROUND_STATE_LAYER`
- Event-Policy `priority + FIFO` ohne Unterbrechung laufender Events
- Aktivierungsbasierter Start der Event-Dauer
- Spezialfaelle als normale Effekte
- Registry-/Discovery-Richtung

### Empirischer Befund

Diese Entscheidungen sind fast vollstaendig im heutigen Verhalten zu finden.

Die Trennung `EffectDefinition` / `EffectInvocation` ist direkt in `src/core/effect_schema.py` implementiert.

Das Rendering ist engine-gezogen. Effekte besitzen kein eigenes `run()`-Loop-Modell; sie liefern nur `render(ctx)`. Die Taktung erfolgt zentral ueber Runtime und Service.

Die Layernamen stimmen exakt mit der Entscheidungsliste ueberein.

Dauer wird konsequent in `ms` gefuehrt, sowohl in `NormalizedCommand`-Parametern als auch in `requested_duration_ms` der Invocation.

Das Prioritaetsmodell entspricht der Entscheidung: `DEFAULT_LAYER_PRIORITIES` in `src/core/effect_schema.py`, `effective_priority()` in `EffectInvocation`, Queue-Sortierung in `src/core/layers.py`.

Die Event-Policy ist behavioristisch sauber umgesetzt:

- nur `EVENT_LAYER` besitzt Queue-Logik
- laufende Events werden nicht preemptet
- neue Events werden nach Prioritaet und bei Gleichstand nach FIFO einsortiert
- die Dauer beginnt erst bei Aktivierung ueber `__activated_at`

Die Spezialfaelle `direction`, `countdown` und `progress` sind normale Effekte in `src/led_effects/effects/` und werden ueber den Normalizer gesetzt.

### Offene oder nur teilweise erreichte Entscheidungen

**Persistenz:**

Die Entscheidung "nur `BACKGROUND_STATE_LAYER` persistent" ist inzwischen end-to-end umgesetzt. `persistent_storage=True` wird an den passenden Layer-Regeln gesetzt, der Service speichert den aktiven Background-State in `runtime_state/background_state.json`, restauriert ihn beim Start und faellt bei fehlender oder ungueltiger Persistenz auf einen gedimmten weissen `solid_color`-Background zurueck.

**`preemptible` fuer Events:**

Die beschlossene Event-Policy ist im Verhalten korrekt umgesetzt. Die Metadatenlage ist jedoch nicht vollstaendig deckungsgleich mit der Entscheidung. `warning_flash` setzt `preemptible=False`, aber `blink_color` ist ebenfalls auf `EVENT_LAYER` erlaubt und behaelt den globalen Default `preemptible=True`. Weil die Runtime aktuell ohnehin keine Event-Preemption ausfuehrt, ist das kein Verhaltensfehler, aber eine kleine semantische Uneinheitlichkeit in den Capabilities.

### Bewertung

Bewertung: ueberwiegend erfuellt.

Die wichtigsten Entscheidungen wurden nicht nur dokumentiert, sondern im Verhalten real umgesetzt. Nach dem spaeteren Persistenzausbau bleibt als groesster offener Punkt vor allem die kleinere Inkonsistenz in der Event-Metadatenbeschreibung.

## 05 Technisches Zielschema

### Kernaussagen des Dokuments

Dokument 05 beschreibt die nahezu direkt implementierbare Zielstruktur fuer:

- `LayerId`, `PlaybackMode`, `CommandKind`, `QueueMode`
- `EffectParamDefinition`, `EffectCapabilities`, `LayerRule`, `EffectDefinition`
- `EffectInvocation`, `LayerState`, `NormalizedCommand`
- `BaseEffect`, `RenderContext`
- `EffectLibrarySource`, `RegisteredEffectType`, `EffectRegistry`
- Discovery-Regeln, Standard-Prioritaeten und Event-Queue-Regel

### Empirischer Befund

Dieses Dokument wurde fast woertlich in Code ueberfuehrt.

Die Enums in `src/core/effect_schema.py` stimmen exakt mit dem Dokumentschema ueberein.

Die Kern-Dataclasses stimmen strukturell fast 1:1 mit dem technischen Zielschema ueberein, einschliesslich `PersistedLayerState`, `EffectInvocation`, `LayerState` und `NormalizedCommand`.

Auch `BaseEffect` und `RenderContext` sind praktisch identisch zum geplanten Schema.

Die Registry-Bausteine `EffectLibrarySource`, `RegisteredEffectType` und `EffectRegistry` existieren in `src/engine/effect_registry.py` und verhalten sich wie geplant: Registrierung, Lookup, Listing, Library-Pfade und Reload sind vorhanden.

Die Discovery-Regeln sind ebenfalls umgesetzt:

- Python-Module laden
- `BaseEffect`-Subklassen finden
- Definition validieren
- eindeutige `effect_id` erzwingen

Die Standard-Prioritaeten in `src/core/effect_schema.py` entsprechen exakt dem geplanten Mapping 100 bis 600.

Die Event-Queue-Regel aus dem Zielschema stimmt mit der Implementierung in `src/core/layers.py` ueberein: laufendes Event bleibt aktiv, Queue wird nach `priority + FIFO` sortiert, Aktivierungszeitpunkt steuert den Beginn der Laufzeit.

### Abweichungen und Restluecken

Das technische Zielschema ist sehr nah getroffen. Die Restluecken liegen nicht in der Form des Schemas, sondern in seiner Vollausnutzung:

- Library-Pfad-Management ist im Registry-Typ vorhanden, aber nicht oeffentlich ueber CLI oder API bedienbar.
- Presets arbeiten noch nicht vollstaendig als reines `effect_id`/Parameter-Mapping, sondern duerfen weiterhin `Visual`-Objekte ueber Kompatibilitaetspfade liefern.

### Bewertung

Bewertung: weitgehend erfuellt.

Von allen Planungsdokumenten ist 05 dasjenige, das am naehesten eins zu eins in Implementierung uebersetzt wurde. Die offenen Punkte liegen ausserhalb des Schemakerns.

## Wichtigste Abweichungen in verdichteter Form

### 1. Persistenz ist inzwischen end-to-end angeschlossen

Vorhanden:

- `PersistedLayerState` als Modell
- `persistent_storage=True` an den relevanten Layer-Regeln
- echte Persistenz-Lade-/Speicherstrecke im Service-Pfad
- Start-Restore aus `runtime_state/background_state.json`
- Fallback auf gedimmtes Weiss bei fehlender oder ungueltiger Persistenz

Nicht vorhanden:

- keine weitergehende Mehrdatei- oder Mehrlayer-Persistenz

Einordnung:

Diese fruehere Restluecke ist inzwischen geschlossen.

### 2. Registry-Erweiterbarkeit ist intern da, aber noch nicht oeffentlich bedienbar

Vorhanden:

- `add_library_path(...)`
- `list_library_sources()`
- `reload()`

Nicht vorhanden:

- CLI- oder API-Endpunkte fuer Library-Path-Management

Einordnung:

Das Kernkonzept ist erreicht, die operative Bedienoberflaeche dazu noch nicht.

### 3. Presets haengen noch an der Legacy-Visual-Kompatibilitaet

Vorhanden:

- Presets laufen innerhalb derselben Runtime und umgehen die Engine nicht
- `legacy_visual` ist als offizieller Kompatibilitaetseffekt vorhanden

Nicht vorhanden:

- vollstaendige Preset-Umstellung auf rein registrierte Effekt-IDs mit Parametern

Einordnung:

Das ist eine bewusst verbleibende Kompatibilitaetsschicht, keine Rueckkehr zur alten Parallelengine. Es ist aber noch nicht die sauberste Endform der Planung.

### 4. Event-Metadaten sind minimal inkonsistent, Verhalten aber korrekt

Vorhanden:

- Queue-Verhalten ohne Preemption des laufenden Events
- Aktivierungsbasierter Start der Event-Dauer

Leichte Inkonsistenz:

- nicht alle eventfaehigen Effektdefinitionen spiegeln `preemptible=False` explizit in ihren Capabilities

Einordnung:

Das ist derzeit eher ein Modellierungsdetail als ein Laufzeitproblem.

## Positiv ueber den Plan hinaus

Der aktuelle Stand geht an einigen Stellen ueber die urspruenglichen Planungen hinaus:

- eine spaeter ausgegliederte dateibasierte Effektbibliothek unter `src/led_effects/effects/`
- direkte Service-Kommandos fuer `list-effects`, `apply-effect` und `clear-layer`
- eine ueber die Kernmigration hinaus weiter gefestigte Testsuite

Das aendert den Planabgleich nicht direkt, zeigt aber, dass die neue Architektur nicht nur migriert, sondern bereits produktiv erweiterbar ist.

## Schlussbewertung

Wenn man die Planungsdokumente 01 bis 05 als Massstab nimmt, ist das Ergebnis heute wie folgt einzuordnen:

- das Zielmodell der neuen Engine ist erreicht
- die wesentlichen Architekturentscheidungen sind im Verhalten realisiert
- das technische Schema wurde sehr nah bis nahezu woertlich umgesetzt
- die Migrationsphasen aus dem Umbauplan sind praktisch abgeschlossen

Offen geblieben sind vor allem Endkonsolidierung und Ausbaupunkte, nicht mehr die Grundarchitektur.

Die treffendste Zusammenfassung lautet daher:

Die Umstrukturierung hat die urspruenglichen Planungen im Kern klar erreicht. Die verbleibenden Abweichungen betreffen vor allem Persistenzvollausbau, Registry-Bedienung und die letzte Bereinigung von Kompatibilitaetspfaden.