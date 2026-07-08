# Das Finale Effekte-Modell

1. Das finale Zielmodell
2. Konsequenz fuer die Dateiformate
3. Identitaet und Namen
4. Wie Metadaten kuenftig abgefragt werden sollen
5. Validierungsregeln fuer eingebettete Presets und Commands
6. Konsequenz fuer die Runtime und Registries
7. Einheitliche Standardparameter
8. Das neue endgültige Modell fuer Standard-Builtins
9. Weitere Wichtige Anmerkungen

## 1. Das finale Zielmodell

### 1.1 Effect

Der Effekt bleibt die eigentliche parametrisierbare Render-Einheit.

Er enthaelt:

- Renderlogik
- `parameter_schema`
- Defaults
- Layer-Regeln
- Capabilities
- Metadaten wie Titel, Beschreibung und Tags

Er bleibt frei parametrisierbar und direkt aufrufbar.

### 1.2 Embedded Effect Presets

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

### 1.3 Embedded Effect Commands

Jede `.lefx` darf null oder mehr eingebettete Commands enthalten.

Diese Commands triggern vorzugsweise die eingebetteten Presets dieses Effekts.

Also:

- `Command -> Preset -> Effect`

Der direkte Pfad

- `Command -> Effect`

ist nur noch als technische Ausnahme zulaessig, aber nicht mehr der bevorzugte Modellstil.

### 1.4 Effect Set

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

## 2. Konsequenz fuer die Dateiformate

### 2.1 Neues Ziel fuer Effekt-Source-Verzeichnisse

Ein einzelner Effekt-Source-Ordner sollte kuenftig so aussehen:

```text
my_effect/
  effect.yaml
  presets.yaml
  commands.json
  effect.py
  assets/
  extra/
```

Dabei gilt:

- `effect.yaml` ist Pflicht
- `presets.yaml` ist streng betrachtet optional, sollte jedoch trotzdem möglichst angegeben werden.
- `commands.json` ist streng betrachtet optional, sollte jedoch trotzdem möglichst angegeben werden.

### 2.2 Neues Ziel fuer `.lefx`

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

### 2.3 Neues Ziel fuer Effekt-Sets

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
`presets.yaml` auf Set-Ebene faellt ebenfalls weg.

### 2.4 Neues Ziel fuer `.lefxset`

Ein gebautes `.lefxset` enthaelt nur noch:

- Set-Manifest
- eingebundene `.lefx`
- Hashes

Die im Set enthaltenen Commands und Presets kommen immer aus den jeweiligen `.lefx`.

## 3. Identitaet und Namen

### 3.1 Effect-ID

Unveraendert:

- `qualified_effect_id = source_id::effect_id`

### 3.2 Preset-ID

Neu:

- `qualified_preset_id = source_id::preset_id`

Da das Preset an einen einzelnen Effekt gebunden ist, sollte `preset_id` innerhalb einer Quelle eindeutig sein.

Ich wuerde deshalb nicht nur auf freie Namen setzen, sondern auf eine klare Namenskonvention.

### 3.3 Empfohlene Preset-Namenskonvention

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

### 3.4 Command-Namen

Bei Commands wuerde ich denselben Gedanken anwenden.

Auch dort kann die Benennung mit Praefixen sinnvoll sein, aber die fachliche Einordnung sollte aus dem Modell kommen, nicht nur aus dem Namen.

Also:

- `kind` bleibt Pflicht
- zusaetzliche Gruppierung in API/CLI ist erlaubt
- Namenspraefixe sind empfohlen, aber nicht die einzige Wahrheitsquelle

## 4. Wie Metadaten kuenftig abgefragt werden sollen

Hier wuerde ich bewusst von deinem Vorschlag abweichen:

Metadaten werden **nicht** als Commands abgebildet.

Also **FALSCH**:

- `soft_pulsing_ring.title`
- `soft_pulsing_ring.params`
- `soft_pulsing_ring.info`

Sondern **RICHTIG**::

- strukturierte Effekt-Info-Endpunkte
- strukturierte Listen fuer Presets und Commands eines Effekts

### 4.1 Warum keine Info-Commands

Info-Commands waeren aus meiner Sicht ungluecklich, weil sie:

- das Command-Konzept fachlich aufweichen
- Listen und Metadaten in ein Aktionsmodell mischen
- API und CLI schwerer konsistent machen
- spaetere UI-Modelle unnoetig komplizierter machen

Commands sollten Aktionen ausloesen.
Informationen sollten abgefragt werden.

### 4.2 Empfohlene API fuer Effekt-Metadaten

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

### 4.3 CLI-Entsprechung

CLI-seitig wuerde ich spiegeln:

- `list-effects`
- `show-effect <qualified_effect_id>`
- `list-effect-presets <qualified_effect_id>`
- `list-effect-commands <qualified_effect_id>`
- `apply-effect <qualified_effect_id> --params ...`
- `apply-effect-preset <qualified_preset_id>`

## 5. Validierungsregeln fuer eingebettete Presets und Commands

Damit das Modell wirklich rund ist, wuerde ich diese Regeln hart setzen.

### 5.1 Preset-Regeln

- Preset-ID innerhalb der Quelle eindeutig
- Preset-Kategorie vorhanden
- Namenspraefix passt zur Kategorie
- `target_layer` ist gesetzt
- `target_layer` passt zur Kategorie
- der Effekt unterstuetzt diesen Layer
- alle gesetzten Params existieren im `parameter_schema`
- alle Parametertypen und Werte sind valide

### 5.2 Command-Regeln

- Command-Name innerhalb der Quelle eindeutig
- `kind` ist gesetzt
- referenziertes Preset existiert
- Command-Kind passt zur Preset-Kategorie
- `off` ist bei Toggle-Commands semantisch konsistent

### 5.3 Set-Regeln

- alle `.lefx` im Set haben dieselbe `source_id`
- `qualified_effect_id`s sind eindeutig
- `qualified_preset_id`s sind eindeutig
- Command-Namen sind innerhalb der Quelle eindeutig

Damit wird ein Set beim Laden einfach zur Vereinigungsmenge aller eingebetteten Inhalte seiner `.lefx`.

## 6. Konsequenz fuer die Runtime und Registries

Ich wuerde die Runtime kuenftig klar in drei Registries trennen:

- `EffectRegistry`
- `EffectPresetRegistry`
- `EffectCommandRegistry`

Das alte heutige `PresetRegistry`-System wuerde ich komplett entfernen.

Das entspricht auch deinem Wunsch:

- kein Sonderweg
- keine Abwaertskompatibilitaet
- sauberes Zielmodell

### 6.1 Entfernung des bisherigen Preset-Systems

Das Alte System/Begriff Presets wurde bereits aus dem Projekt entfernt...

Ab sofort gibt es nur noch:
eingebettete Effect Presets

Das macht die Sprache und die Architektur deutlich klarer.

## 7. Einheitliche Standardparameter

Hier ist dein Einwand zu `ring_effects.py` aus meiner Sicht absolut berechtigt.

Die heutige Loesung mit nachtraeglichem allgemeinem `brightness`-Injection ist nicht sauber genug fuer ein rundes Zielkonzept.

Wenn wir das neue Gesamtmodell jetzt festziehen wollen, sollten wir auch die Standardparameter einmal konsequent definieren.

### 7.1 Ziel

Bestimmte Parameter sollen kuenftig eine feste, allgemeingueltige Bedeutung haben.

Nicht als Zufallsprodukt einzelner Effekte, sondern als bewusst definierter Standard.

### 7.2 Empfohlene Standardparameter

#### `color`

Primäre Vordergrundfarbe des Effekts.

#### `background_color`

Hintergrundfarbe oder Basisfarbe des Effekts.

Ich wuerde kuenftig nur noch `background_color` als Standardnamen verwenden.
`base_color` sollte nicht weiter als paralleler Primärname bestehen bleiben.

#### `brightness`

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

#### `min_brightness`

Optionaler unterer Helligkeitswert fuer pulsierende oder weich animierte Effekte.

#### `speed`

Allgemeiner Geschwindigkeitsparameter fuer animierte Effekte.

Regel:

- alle zeitlich animierten Effekte sollen, sofern sinnvoll, `speed` unterstuetzen
- `speed = 1.0` bedeutet die normale Referenzgeschwindigkeit des Effekts
- `speed = 0.0` bedeutet Stillstand oder keine zeitliche Veraenderung, sofern fachlich sinnvoll

#### `direction`

Allgemeiner Richtungsparameter fuer laufende oder rotierende Effekte.

#### `duration_ms`

Allgemeiner Dauerparameter fuer endliche Event- oder Einmal-Effekte.

### 7.3 Neue Konventionen fuer First-Party-Effekte

Ich wuerde fuer First-Party-Effekte diese Pflichtregeln setzen:

1. Wenn ein Effekt animiert ist, soll er `speed` verwenden.
2. Wenn ein Effekt sinnvoll global dimmbar ist, soll er `brightness` verwenden.
3. Wenn ein Effekt eine Helligkeitsspanne braucht, verwendet er `brightness` plus optional `min_brightness`.
4. `max_brightness` wird in neuen oder migrierten First-Party-Effekten nicht mehr verwendet.
5. `background_color` ist der Standardname fuer Hintergrund/Basisfarbe.

### 7.4 Konsequenz fuer `ring_effects.py`

Das bedeutet ganz konkret:

- die nachtraegliche `_enable_general_brightness(...)`-Loesung sollte entfallen
- die betroffenen Effekte sollen ihre Standardparameter explizit selbst definieren
- `max_brightness`-Faelle sollen auf das neue Modell umgestellt werden

Also zum Beispiel:

- `brightness` statt `max_brightness`
- `brightness` plus `min_brightness` statt `min_brightness` plus `max_brightness`

Das ist fachlich klarer und technisch wesentlich sauberer.

## 8. Das neue endgültige Modell fuer Effekte

- Standard-Builtin-Effekte werden grundsätzlich wie alle anderen Befehle behandelt, Ausnahmen davon werden unter 8.1 erklärt.

### 8.1 Das Privileg der Standard-Builtin-Effekte

- Die Standard-Builtins werden, wie alle anderen effekte, in .lefx-Dateien definiert, inklusive presets und commands.
- Alle lefx-Dateien der Standard-Effekte werden in der lefxset-Datei mit der source-id "default-effects" zusammengefasst.
- Die lefxset-Datei mit dem "default-effects"-Set wird als einzige Effekt-Quelle in den Build des led_controller eingebettet.
- Die Standard-Effekte haben zusätzlich das Privileg, dass sie zusätzlich ohne source-angabe verwendet werden können.
- Beispiele:
  - `default-effects::soft_pulsing_ring` oder nur `soft_pulsing_ring`
  - `default-effects::warning_flash` oder nur `warning_flash`
  - `default-effects::timer_ring` oder nur `timer_ring`

### 8.2 Haeufige Varianten werden als eingebettete Presets mitgeliefert

- Presets sind die Parameter festgelegt, sodass sie ohne weitere Angaben ausführbar sind.
- Für andere Konfigurationen müssen deshalb eigene Presets angelegt werden.
Beispiele:

- `state_soft_blue_idle`
- `state_soft_green_waiting`  /* Einziger sichtbarer Unterschied des Effekts zu state_soft_blue_idle ist die Farbe
- `overlay_progress_cyan`
- `event_error_flash_red`

### 8.3 Normalerweise wird für jedes Preset ein eingebetteter Command als Trigger mitgeliefert

Beispiele:

- `state_idle`
- `state_waiting`
- `overlay_progress`
- `event_error_flash`

### 8.4 Der Effekt selbst bleibt trotzdem frei parametrisierbar

Das ist der wichtigste Punkt:

Die eingebetteten Presets und Commands ersetzen die freie Parametrierung nicht.
Sie ergaenzen sie nur.

Damit haben wir beides:

- kuratierte, feste Bedienpunkte
- und volle Ausdruckskraft fuer direkte API- oder interne Aufrufe

## 9. Weitere Wichtige Anmerkungen

### 9.1 Building der `.lefx` und `.lefxset`-Dateien

- Alle Effekte sollen nach dem neuen Effekte-Modell wie zuvor beschrieben in `.lefx`-Dateien definiert werden, auch die default/builtin-Effekte.
- Das Building der `.lefx` und `.lefxset`  komplett unabhängig mit eigenständigen Scripts/Tools sein soll. Das soll deshalb insgesamt nur innerhalb des Ordners "tools\effect_building" stattfinden.
- Der `.lefx`-build-flow soll die fertigen `.lefx`-Dateien in "tools\effect_building\build_lefx\<source_id>" speichern.
- Der `.lefxset`-build-flow soll aus diesen <source_id>-Ordnern die enthaltenen `.lefx`-Dateien in eine `.lefxset`-Datei zusammenpacken und unter in "tools\effect_building\build_lefxset\<source_id>.lefxset" speichern. Dafür soll es ein eigenes Script geben ("tools\effect_building\build_lefxset.py")

### 9.2 Letzte Anmerkungen zum aktuellen Stand

- Die Logik des eigentlichen led_controller-Service soll lediglich mit den fertigen `.lefx` und `.lefxset` umgehen können,d.h. sie lesen um die die effekte, presets und commands zu registrieren und korrekt wiedergeben können.
- Der Build der `.lefx` und `.lefxset` -Dateien ist strikt davon zu trennen.
- Die bisherige Definition der Effects aus "src\led_effects\effects" soll in das neue System überführt werden, sodass es einheitlich nurnoch dieses eine Modell gibt.
- Es gab bereits einen Implementierungsversuch, der jedoch nicht richtig war. Deshalb überprüfe im Ordner "src/engine" die Dateien "effect_preset_registry.py", "effect_package_schema.py", "effect_package_builder.py" oder "effect_command_registry.py" und ggfs weitere Dateien, um die Logik korrekt wie hier beschrieben zuschneiden und implementieren zu können, da dort auch Logikteile gelandet sind die dort falsch sind, da sie zum build gehören
