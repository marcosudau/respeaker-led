# Finalisierungskonzept: Effects, eingebettete Presets, eingebettete Commands und einheitliche Standardparameter

Stand: 2026-04-12
Status: konsolidierte Folgefassung auf Basis von `08__10` und `08__11`

## 1. Kurzfazit zu deinen Anmerkungen

Deine Anmerkungen gehen aus meiner Sicht in die richtige Richtung.

Ich wuerde die meisten Punkte uebernehmen:

- altes Preset-System sauber entfernen
- keine Ruecksicht mehr auf Abwaertskompatibilitaet
- Presets direkt an den einzelnen Effekt haengen
- Commands ebenfalls direkt an den einzelnen Effekt haengen
- `.lefxset` wieder auf die Rolle einer reinen Zusammenfassung zurueckfuehren
- die Parameterfrage jetzt einmal insgesamt sauber und allgemeingueltig loesen

Einen Punkt wuerde ich aber bewusst anders schneiden:

Die vorgeschlagenen Informations-Commands wie

- `soft_pulsing_ring.title`
- `soft_pulsing_ring.description`
- `soft_pulsing_ring.params`
- `soft_pulsing_ring.info`

wuerde ich **nicht** als Commands modellieren.

Mein Grund dafuer ist einfach:

Commands sollen Aktionen ausloesen.
Metadaten sollen ueber strukturierte Info-Endpunkte und List-Abfragen kommen.

Das ist sauberer, leichter testbar und macht das Gesamtsystem konzeptionell klarer.

## 2. Neue Grundentscheidung

Auf Basis deiner Anmerkungen wuerde ich das Zielmodell jetzt so festziehen:

1. `Effect`
2. `Embedded Effect Presets`
3. `Embedded Effect Commands`
4. `Effect Set` nur noch als Aggregation

Also:

- die einzelne `.lefx` ist die inhaltlich vollstaendige Einheit
- das `.lefxset` gruppiert mehrere `.lefx`
- Presets und Commands werden nicht auf Set-Ebene definiert
- ein Set fuegt keine eigene fachliche Logik hinzu

Das ist aus meiner Sicht runder als die vorherige Zwischenidee mit Set-weiten Presets.

## 3. Das finale Zielmodell

## 3.1 Effect

Der Effekt bleibt die eigentliche parametrisierbare Render-Einheit.

Er enthaelt:

- Renderlogik
- `parameter_schema`
- Defaults
- Layer-Regeln
- Capabilities
- Metadaten wie Titel, Beschreibung und Tags

Er bleibt frei parametrisierbar und direkt aufrufbar.

## 3.2 Embedded Effect Presets

Jede `.lefx` darf null oder mehr eingebettete Presets enthalten.

Ein Preset beschreibt:

- eine benannte haeufige Verwendung dieses einen Effekts
- den Ziel-Layer
- feste Parameterwerte
- optional Dauer und weitere Invocation-Optionen

Wichtig:

Ein Preset gehoert immer genau zu einem Effekt.
Es referenziert also nicht beliebig andere Effekte derselben Quelle.

Das macht die einzelne `.lefx` wirklich in sich geschlossen und als Einzelartefakt voll nutzbar.

## 3.3 Embedded Effect Commands

Jede `.lefx` darf null oder mehr eingebettete Commands enthalten.

Diese Commands triggern vorzugsweise die eingebetteten Presets dieses Effekts.

Also:

- `Command -> Preset -> Effect`

Der direkte Pfad

- `Command -> Effect`

ist nur noch als technische Ausnahme zulaessig, aber nicht mehr der bevorzugte Modellstil.

## 3.4 Effect Set

Das `.lefxset` wird wieder konsequent auf eine Rolle reduziert:

- Sammlung mehrerer `.lefx`
- gemeinsame `source_id`
- gemeinsame Verteilung, Registrierung und Aktivierung

Nicht mehr Teil des Sets:

- eigene Presets
- eigene Commands
- eigene zusaetzliche fachliche Steuerlogik

Damit ist ein Set wirklich nur noch das, was du beschrieben hast:

die Zusammenfassung mehrerer einzelner, bereits vollstaendiger Effekte.

## 4. Konsequenz fuer die Dateiformate

## 4.1 Neues Ziel fuer Effekt-Source-Verzeichnisse

Ein einzelner Effekt-Source-Ordner sollte kuenftig so aussehen:

```text
my_effect/
  effect.yaml
  effect-presets.yaml
  commands.json
  effect.py
  assets/
  extra/
```

Dabei gilt:

- `effect.yaml` ist Pflicht
- `effect-presets.yaml` ist optional
- `commands.json` ist optional

## 4.2 Neues Ziel fuer `.lefx`

Ein gebautes `.lefx` enthaelt kuenftig nicht nur den Effekt selbst, sondern optional auch dessen eingebettete Presets und Commands.

Empfohlenes Archivmodell:

```text
manifest.json
effect-presets.json
commands.json
payload/...
hashes.json
```

Dabei gilt:

- `manifest.json` ist Pflicht
- `effect-presets.json` ist optional
- `commands.json` ist optional

## 4.3 Neues Ziel fuer Effekt-Sets

Ein Set-Source-Ordner wird deutlich einfacher:

```text
my_set/
  set.yaml
  effects/
    effect_a.lefx
    effect_b.lefx
    effect_c.lefx
```

`commands.json` auf Set-Ebene faellt weg.
`effect-presets.yaml` auf Set-Ebene faellt ebenfalls weg.

## 4.4 Neues Ziel fuer `.lefxset`

Ein gebautes `.lefxset` enthaelt nur noch:

- Set-Manifest
- eingebundene `.lefx`
- Hashes

Die im Set enthaltenen Commands und Presets kommen immer aus den jeweiligen `.lefx`.

## 5. Identitaet und Namen

## 5.1 Effect-ID

Unveraendert:

- `qualified_effect_id = source_id::effect_id`

## 5.2 Preset-ID

Neu:

- `qualified_preset_id = source_id::preset_id`

Da das Preset an einen einzelnen Effekt gebunden ist, sollte `preset_id` innerhalb einer Quelle eindeutig sein.

Ich wuerde deshalb nicht nur auf freie Namen setzen, sondern auf eine klare Namenskonvention.

## 5.3 Empfohlene Preset-Namenskonvention

Dein Vorschlag mit Praefixen ist gut.

Ich wuerde ihn uebernehmen, aber nicht nur als Konvention, sondern zusaetzlich mit einer expliziten Kategorie im Presetmodell absichern.

Empfohlen:

- `category: state | effect | overlay | event`

Und zusaetzlich als Namenskonvention:

- `state_*`
- `effect_*`
- `overlay_*`
- `event_*`

Warum beides:

- der Praefix hilft Menschen beim Lesen
- die Kategorie hilft der Maschine bei Filterung, Validierung und API-Ausgabe

Nur auf String-Praefixe zu vertrauen waere mir auf Dauer zu fragil.

## 5.4 Command-Namen

Bei Commands wuerde ich denselben Gedanken anwenden.

Auch dort kann die Benennung mit Praefixen sinnvoll sein, aber die fachliche Einordnung sollte aus dem Modell kommen, nicht nur aus dem Namen.

Also:

- `kind` bleibt Pflicht
- zusaetzliche Gruppierung in API/CLI ist erlaubt
- Namenspraefixe sind empfohlen, aber nicht die einzige Wahrheitsquelle

## 6. Wie Metadaten kuenftig abgefragt werden sollen

Hier wuerde ich bewusst von deinem Vorschlag abweichen:

Metadaten sollten **nicht** als Commands abgebildet werden.

Also nicht:

- `soft_pulsing_ring.title`
- `soft_pulsing_ring.params`
- `soft_pulsing_ring.info`

Sondern:

- strukturierte Effekt-Info-Endpunkte
- strukturierte Listen fuer Presets und Commands eines Effekts

## 6.1 Warum keine Info-Commands

Info-Commands waeren aus meiner Sicht ungluecklich, weil sie:

- das Command-Konzept fachlich aufweichen
- Listen und Metadaten in ein Aktionsmodell mischen
- API und CLI schwerer konsistent machen
- spaetere UI-Modelle unnoetig komplizierter machen

Commands sollten Aktionen ausloesen.
Informationen sollten abgefragt werden.

## 6.2 Empfohlene API fuer Effekt-Metadaten

Ich wuerde die API so erweitern:

- `GET /api/v1/effects`
- `GET /api/v1/effects/{source_id}`
- `GET /api/v1/effects/{source_id}/{effect_id}`
- `GET /api/v1/effects/{source_id}/{effect_id}/presets`
- `GET /api/v1/effects/{source_id}/{effect_id}/commands`

Optional zusaetzlich:

- `POST /api/v1/effects/{source_id}/{effect_id}/apply`
- `POST /api/v1/effects/{source_id}/{effect_id}/presets/{preset_id}/apply`

Damit bekommt man genau die von dir gewuenschte Informationsdichte, aber auf einem sauberen Weg.

## 6.3 CLI-Entsprechung

CLI-seitig wuerde ich spiegeln:

- `list-effects`
- `show-effect <qualified_effect_id>`
- `list-effect-presets <qualified_effect_id>`
- `list-effect-commands <qualified_effect_id>`
- `apply-effect <qualified_effect_id> --params ...`
- `apply-effect-preset <qualified_preset_id>`

## 7. Validierungsregeln fuer eingebettete Presets und Commands

Damit das Modell wirklich rund ist, wuerde ich diese Regeln hart setzen.

## 7.1 Preset-Regeln

- Preset-ID innerhalb der Quelle eindeutig
- Preset-Kategorie vorhanden
- Namenspraefix passt zur Kategorie
- `target_layer` ist gesetzt
- `target_layer` passt zur Kategorie
- der Effekt unterstuetzt diesen Layer
- alle gesetzten Params existieren im `parameter_schema`
- alle Parametertypen und Werte sind valide

## 7.2 Command-Regeln

- Command-Name innerhalb der Quelle eindeutig
- `kind` ist gesetzt
- referenziertes Preset existiert
- Command-Kind passt zur Preset-Kategorie
- `off` ist bei Toggle-Commands semantisch konsistent

## 7.3 Set-Regeln

- alle `.lefx` im Set haben dieselbe `source_id`
- `qualified_effect_id`s sind eindeutig
- `qualified_preset_id`s sind eindeutig
- Command-Namen sind innerhalb der Quelle eindeutig

Damit wird ein Set beim Laden einfach zur Vereinigungsmenge aller eingebetteten Inhalte seiner `.lefx`.

## 8. Konsequenz fuer die Runtime und Registries

Ich wuerde die Runtime kuenftig klar in drei Registries trennen:

- `EffectRegistry`
- `EffectPresetRegistry`
- `EffectCommandRegistry`

Das alte heutige `PresetRegistry`-System wuerde ich komplett entfernen.

Das entspricht auch deinem Wunsch:

- kein Sonderweg
- keine Abwaertskompatibilitaet
- sauberes Zielmodell

## 8.1 Entfernung des bisherigen Preset-Systems

Ich halte das fuer sinnvoll.

Heute ist dieses System zwar vorhanden, aber fachlich nicht in den neuen Paketweg integriert und praktisch offenbar ohne reale Nutzung.

Deshalb mein klares Votum:

- komplett entfernen
- Dokumentation mit bereinigen
- API/CLI daraufhin bereinigen
- intern den Begriff `PresetRegistry` nicht weiter mitziehen

Danach gibt es nur noch:

- eingebettete Effect Presets

Das macht die Sprache und die Architektur deutlich klarer.

## 9. Einheitliche Standardparameter

Hier ist dein Einwand zu `ring_effects.py` aus meiner Sicht absolut berechtigt.

Die heutige Loesung mit nachtraeglichem allgemeinem `brightness`-Injection ist nicht sauber genug fuer ein rundes Zielkonzept.

Wenn wir das neue Gesamtmodell jetzt festziehen wollen, sollten wir auch die Standardparameter einmal konsequent definieren.

## 9.1 Ziel

Bestimmte Parameter sollen kuenftig eine feste, allgemeingueltige Bedeutung haben.

Nicht als Zufallsprodukt einzelner Effekte, sondern als bewusst definierter Standard.

## 9.2 Empfohlene Standardparameter

### `color`

Primäre Vordergrundfarbe des Effekts.

### `background_color`

Hintergrundfarbe oder Basisfarbe des Effekts.

Ich wuerde kuenftig nur noch `background_color` als Standardnamen verwenden.
`base_color` sollte nicht weiter als paralleler Primärname bestehen bleiben.

### `brightness`

Allgemeiner Intensitaets- bzw. Maximalhelligkeitsparameter.

Regel:

- wenn ein Effekt eine globale Helligkeitssteuerung sinnvoll unterstuetzt, heisst sie `brightness`
- Wertebereich immer `0.0 .. 1.0`

Wichtige neue Festlegung:

Bei Effekten mit Helligkeitsspanne ist `brightness` der obere bzw. wirksame Hauptwert.

Also nicht:

- nur `max_brightness`

sondern:

- `brightness`
- optional zusaetzlich `min_brightness`

Das uebernimmt genau deinen Vorschlag.

### `min_brightness`

Optionaler unterer Helligkeitswert fuer pulsierende oder weich animierte Effekte.

### `speed`

Allgemeiner Geschwindigkeitsparameter fuer animierte Effekte.

Regel:

- alle zeitlich animierten Effekte sollen, sofern sinnvoll, `speed` unterstuetzen
- `speed = 1.0` bedeutet die normale Referenzgeschwindigkeit des Effekts
- `speed = 0.0` bedeutet Stillstand oder keine zeitliche Veraenderung, sofern fachlich sinnvoll

### `direction`

Allgemeiner Richtungsparameter fuer laufende oder rotierende Effekte.

### `duration_ms`

Allgemeiner Dauerparameter fuer endliche Event- oder Einmal-Effekte.

## 9.3 Neue Konventionen fuer First-Party-Effekte

Ich wuerde fuer First-Party-Effekte diese Pflichtregeln setzen:

1. Wenn ein Effekt animiert ist, soll er `speed` verwenden.
2. Wenn ein Effekt sinnvoll global dimmbar ist, soll er `brightness` verwenden.
3. Wenn ein Effekt eine Helligkeitsspanne braucht, verwendet er `brightness` plus optional `min_brightness`.
4. `max_brightness` wird in neuen oder migrierten First-Party-Effekten nicht mehr verwendet.
5. `background_color` ist der Standardname fuer Hintergrund/Basisfarbe.

## 9.4 Konsequenz fuer `ring_effects.py`

Das bedeutet ganz konkret:

- die nachtraegliche `_enable_general_brightness(...)`-Loesung sollte entfallen
- die betroffenen Effekte sollen ihre Standardparameter explizit selbst definieren
- `max_brightness`-Faelle sollen auf das neue Modell umgestellt werden

Also zum Beispiel:

- `brightness` statt `max_brightness`
- `brightness` plus `min_brightness` statt `min_brightness` plus `max_brightness`

Das ist fachlich klarer und technisch wesentlich sauberer.

## 10. Das neue endgültige Modell fuer Standard-Builtins

Mit allen bisherigen Diskussionen zusammen wuerde ich die Standard-Builtins jetzt so ueberfuehren:

## 10.1 Jeder Standardeffekt wird eine First-Party-`.lefx`

Beispiele:

- `default-effects::soft_pulsing_ring`
- `default-effects::warning_flash`
- `default-effects::timer_ring`

## 10.2 Haeufige Varianten werden als eingebettete Presets mitgeliefert

Beispiele:

- `state_idle_soft_blue`
- `overlay_direction_cyan`
- `event_error_flash_red`

## 10.3 Nur wirklich noetige Trigger werden als eingebettete Commands mitgeliefert

Beispiele:

- `state_idle`
- `overlay_direction`
- `event_error_flash`

## 10.4 Der Effekt selbst bleibt trotzdem frei parametrisierbar

Das ist der wichtigste Punkt:

Die eingebetteten Presets und Commands ersetzen die freie Parametrierung nicht.
Sie ergaenzen sie nur.

Damit haben wir beides:

- kuratierte, feste Bedienpunkte
- und volle Ausdruckskraft fuer direkte API- oder interne Aufrufe

## 11. Empfohlener Implementierungsplan

Wenn wir das jetzt ohne Ruecksicht auf Altlasten durchziehen, wuerde ich genau diese Reihenfolge empfehlen.

## Phase A: Altes Preset-System entfernen

- `PresetRegistry` entfernen
- zugehoerige Loader und API/CLI-Pfade entfernen
- Doku bereinigen

## Phase B: `.lefx` um eingebettete Presets und Commands erweitern

- Source-Format erweitern
- Builder erweitern
- Loader erweitern
- neue Registries einfuehren

## Phase C: `.lefxset` auf reine Aggregation umstellen

- Set-Source vereinfachen
- Set-Builder vereinfachen
- Set-Loader aggregiert Presets und Commands aus den `.lefx`

## Phase D: API und CLI auf das Endmodell bringen

- Info-Endpunkte fuer Effekte
- Listen fuer Presets und Commands pro Effekt
- Apply-Endpunkte fuer Effekt und Preset
- Command-Aufrufe bleiben triggerbasiert

## Phase E: First-Party-Builtins migrieren und Standardparameter bereinigen

- Standardeffekte als `.lefx` modellieren
- `brightness`/`speed`/`background_color` vereinheitlichen
- `_enable_general_brightness(...)` entfernen
- kuratierte Presets und Commands definieren

## 12. Die Entscheidungen, die ich jetzt festziehen wuerde

Damit danach praktisch nur noch Umsetzung uebrig bleibt, wuerde ich diese Punkte jetzt als Zielentscheidung setzen.

### Entscheidung 1

Das alte Preset-System wird komplett entfernt.

Meine Empfehlung:

- ja

### Entscheidung 2

Presets und Commands werden an der einzelnen `.lefx` definiert, nicht am `.lefxset`.

Meine Empfehlung:

- ja

### Entscheidung 3

`.lefxset` ist nur noch Aggregation und Distribution, keine eigene fachliche Konfigurationsschicht mehr.

Meine Empfehlung:

- ja

### Entscheidung 4

Informationsabfragen werden ueber API/CLI-Metadatenpfade geloest, nicht ueber Info-Commands.

Meine Empfehlung:

- ja

### Entscheidung 5

Fuer First-Party-Effekte gelten kuenftig feste Standardparameterregeln, insbesondere `brightness`, `speed` und `background_color`.

Meine Empfehlung:

- ja

## 13. Mein Schlussfazit

Mit deinen Anmerkungen wird das Konzept aus meiner Sicht nicht nur besser, sondern deutlich runder.

Die entscheidende Verbesserung ist:

Die `.lefx` wird jetzt zur wirklich vollstaendigen fachlichen Einheit:

- Effekt
- Presets
- Commands
- Metadaten

Und das `.lefxset` wird wieder das, was es sein sollte:

- eine reine Zusammenfassung mehrerer solcher Einheiten

Dazu kommt mit den neuen Standardparameterregeln endlich auch eine saubere Linie fuer Dinge wie `brightness` und `speed`.

Wenn wir diesen Kurs jetzt festziehen, ist das aus meiner Sicht die bislang rundeste und konsistenteste Endfassung des Gesamtkonzepts.
