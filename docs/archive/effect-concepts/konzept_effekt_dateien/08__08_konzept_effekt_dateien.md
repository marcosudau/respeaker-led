# Folgekonzept: Weiterentwicklung des Effect-Building

Stand: 2026-04-12
Status: Konzept fuer die naechste Ausbaustufe des Effect-Building, noch ohne Implementierung

## 1. Einordnung

Die Ideen aus `08__07_konzept_effekt_dateien.md` sind sinnvoll und passen gut auf die bereits umgesetzte V1 auf.

Die aktuelle V1 kann bereits:

- einzelne Effektquellen aus lesbaren Source-Ordnern zu `.lefx` bauen
- Effektsets aus Source-Ordnern zu `.lefxset` bauen
- Pakete inspizieren und verifizieren
- `.lefxset` live registrieren und abspielen

Was aktuell noch fehlt, ist vor allem eine komfortablere Authoring- und Build-Schicht.

Genau dort setzen deine Ideen an. Aus meiner Sicht ist das der richtige nächste Schritt.

## 2. Gesamtbewertung deiner Ideen

Die Vorschlaege sind insgesamt stark, weil sie drei echte Schwachstellen der aktuellen V1 adressieren:

1. Das Anlegen neuer Effektquellen ist noch zu manuell.
2. Das Authoring-Format ist noch zu nah an der internen Python-Struktur.
3. Das Zusammenbauen von Sets ist aktuell source-dir-basiert und noch nicht streng genug ueber bereits gebaute `.lefx` standardisiert.

Meine Kurzbewertung:

- `single-effect`-Scaffolding: sehr sinnvoll
- kommentierte Templates: sehr sinnvoll
- mehrere Effekte in einer JSON-Datei: sinnvoll, aber mit klaren Grenzen
- zusaetzliche Assets und Python-Dateien: sinnvoll und wichtig
- `effect-set` nur aus bereits gebauten `.lefx`: architektonisch sehr stark
- `source_id`-Mismatch im Set-Build: wichtig, aber ich wuerde nicht stillschweigend skippen

Gerade der letzte Punkt ist wichtig:

Das automatische Ueberspringen fremder `source_id`s klingt praktisch, ist aber aus meiner Sicht gefaehrlich, weil es Build-Ergebnisse still veraendert.

Meine Empfehlung waere:

- Standard: harter Fehler bei `source_id`-Mismatch
- optionaler Modus spaeter: `--skip-mismatched-source-id`

## 3. Zielbild fuer die naechste Building-Ausbaustufe

Das Building soll in der naechsten Stufe nicht nur Pakete erzeugen, sondern einen gefuehrten Authoring-Workflow bilden.

Dieser Workflow sollte drei Ebenen abdecken:

1. Scaffold
2. Authoring
3. Build

### 3.1 Scaffold

Ein Tool erzeugt die noetige Grundstruktur fuer neue Effekte automatisch.

### 3.2 Authoring

Effekte koennen nicht nur direkt per Python geschrieben, sondern auch ueber ausgefuellte Manifest-/Definitionsdateien vorbereitet werden.

### 3.3 Build

Die Authoring-Artefakte werden validiert und in `.lefx` oder `.lefxset` ueberfuehrt.

## 4. Konkretes Zielmodell fuer `single-effect (*.lefx)`

## 4.1 Neuer Zweck des Single-Effect-Building

Ein einzelner Effekt soll kuenftig auf zwei Arten entstehen koennen:

1. scaffold-first
2. definition-first

### scaffold-first

Das Tool legt einen neuen Effektordner samt Vorlagen an.

### definition-first

Das Tool liest eine bestehende Definitionsdatei und erzeugt daraus einen oder mehrere Effektordner oder direkt `.lefx`-Artefakte.

## 4.2 Scaffold-Tool fuer einzelne Effekte

Deine Idee ist aus meiner Sicht sehr gut und sollte direkt Teil der naechsten Ausbaustufe werden.

Empfohlener neuer Befehl:

```text
effect_packager.py init-effect
```

Beispiel:

```powershell
python .\tools\effect_packager.py init-effect --target .\my_effects\listening_blue --effect-id listening_blue --source-id app.voice_assistant
```

Dieser Befehl sollte automatisch erzeugen:

```text
listening_blue/
  effect.yaml
  effect.py
  assets/
  extra/
```

### Inhalt der generierten Dateien

`effect.yaml`

- kommentierte oder zumindest gut ausgefuellte Vorlage
- alle Pflichtfelder enthalten
- klare Hinweise auf anpassbare Felder

`effect.py`

- lauffaehiges minimales Beispiel
- fertige `BaseEffect`-Klasse
- passende `definition`
- einfache `render(ctx)`-Beispielstruktur

`assets/`

- leerer Ordner fuer Assets

`extra/`

- optionaler Ordner fuer zusaetzliche Python-Hilfsdateien

## 4.3 Unterstuetzung fuer Assets und zusaetzliche Python-Dateien

Das ist fuer mich ein klares Ja.

Die aktuelle V1 kann bereits alle Dateien ausser den Source-Metadateien in `payload/` mitnehmen. Das sollte im Building jetzt bewusst formalisiert werden.

Empfohlene Regel:

- `effect.py` bleibt der definierte Entry-Point
- weitere Python-Dateien sind erlaubt
- weitere Assets sind erlaubt
- alles wird relativ zum Effektordner in `payload/` uebernommen

Beispiel:

```text
listening_blue/
  effect.yaml
  effect.py
  helper_math.py
  palettes.py
  assets/
    palette.json
    mask.bin
```

Das ist architektonisch sauber, weil:

- der Entry-Punkt explizit bleibt
- Import-Hilfsdateien weiterhin moeglich sind
- komplexere Effekte nicht kuenstlich beschnitten werden

## 4.4 YAML/JSON als definierende Authoring-Datei

Auch das halte ich fuer sinnvoll, aber nur mit einer klaren Begrenzung.

Hier muss man zwischen zwei Rollen unterscheiden:

1. Build-Metadaten
2. Renderlogik

Build-Metadaten koennen sehr gut in YAML oder JSON beschrieben werden.

Renderlogik bleibt in V1 und voraussichtlich auch in V2 weiterhin Python.

Deshalb meine Empfehlung:

- YAML/JSON beschreibt Manifest, Struktur, Metaangaben und Build-Optionen
- Python bleibt fuer die eigentliche Effektlogik verantwortlich

Das vermeidet, dass versehentlich doch wieder eine halbe deklarative Effekt-DSL entsteht.

## 4.5 Kommentiertes Template

Das ist sehr sinnvoll.

Ich wuerde es so umsetzen:

- fuer YAML: echtes kommentiertes Template
- fuer JSON: kein Kommentarformat, daher stattdessen Beispielwerte plus extra `README` oder `template-notes.md`

Meine Empfehlung:

- YAML ist das bessere Primary-Authoring-Format
- JSON bleibt als optionales maschinenfreundliches Format zulaessig

Grund:

- Kommentare in YAML sind fuer Vorlagen und Onboarding klar besser
- JSON ist gut fuer Generatoren oder externe Tools

## 4.6 Mehrere Effekte in einer JSON-Datei

Das ist sinnvoll, aber ich wuerde es nicht als allgemeines Standardformat fuer Handarbeit empfehlen.

Ich wuerde das als Batch-Input fuer Generatoren oder Massenanlage sehen.

### Empfehlung

Unterstuetzen:

- ja

Primärformat fuer Menschen:

- nein

Empfohlenes Einsatzfeld:

- automatisierte Erzeugung vieler Varianten
- Import aus externer Datenquelle
- definierte Farbreihen oder Effektfamilien

Beispiel:

```json
{
  "source_id": "app.voice_assistant",
  "effects": [
    {
      "effect_id": "idle_blue",
      "title": "Idle Blue"
    },
    {
      "effect_id": "idle_green",
      "title": "Idle Green"
    }
  ]
}
```

Das Tool sollte daraus jeweils:

- eigene Effektordner erzeugen oder
- direkt mehrere `.lefx` bauen

Wichtige Begrenzung:

Wenn mehrere Effekte in einer Datei definiert werden, sollte das nur die Metadaten- und Scaffold-Schicht betreffen.

Die eigentliche Python-Renderlogik muss trotzdem klar aufloesbar bleiben.

Sonst wird das Modell schnell unsauber.

## 4.7 Validierung

Hier bin ich voll bei dir: Das Tool muss frueh und hart validieren.

Es sollte mindestens pruefen:

- Pflichtfelder vorhanden
- `effect_id` gueltig
- `source_id` vorhanden
- `entry_class` plausibel
- `effect.py` vorhanden
- referenzierte Zusatzdateien vorhanden
- geladenes Python-Modul enthaelt die passende Klasse
- `EffectDefinition` stimmt mit Metadaten ueberein

Meine Empfehlung:

Validation in drei Stufen:

1. Strukturvalidierung
2. Metadatenvalidierung
3. Runtime-nahe Validierung durch Import der Effektklasse

## 5. Konkretes Zielmodell fuer `effect-set (*.lefxset)`

## 5.1 Der von dir vorgeschlagene Zwischenschritt ueber `.lefx`

Das halte ich fuer eine sehr gute Idee und sogar fuer die sauberere Architektur.

Ich wuerde das kuenftig als Standard festlegen:

- Ein `.lefxset` wird aus bereits gebauten `.lefx`-Dateien erstellt.
- Der Set-Builder baut nicht mehr implizit aus Effekt-Source-Ordnern.

Das ist besser, weil:

- der Build-Prozess klar gestuft wird
- einzelne Effekte zuerst fuer sich validiert werden
- Set-Build nur noch Packaging und Gruppierung ist
- Fehlersuche einfacher wird

### Mein klares Votum

Ja, das sollte die bevorzugte Zielarchitektur sein.

## 5.2 Empfohlener kuenftiger Set-Source-Aufbau

Ich wuerde fuer den Set-Builder kuenftig eher so denken:

```text
my_set/
  set.yaml
  commands.json
  effects/
    idle_blue.lefx
    listening_blue.lefx
    event_error.lefx
```

Das waere klarer als der heutige indirekte Zwischenweg ueber Effekt-Source-Ordner.

## 5.3 Umgang mit `source_id`

Hier stimme ich dem Grundgedanken zu, aber nicht ganz der vorgeschlagenen Laufzeitreaktion.

### Fachlich richtig

Ja, alle `.lefx` innerhalb eines `.lefxset` sollten dieselbe `source_id` tragen.

### Aber:

Ein stilles "Datei ueberspringen und nicht mit aufnehmen" ist aus meiner Sicht zu weich.

Warum problematisch:

- ein Set wird dann anders gebaut als erwartet
- Fehler bleiben moeglicherweise unbemerkt
- `commands.json` kann danach auf fehlende Effekte zeigen
- Build-Artefakt wird inkonsistent, obwohl der Build formal "durchlief"

### Meine Empfehlung

Standardverhalten:

- harter Fehler

Optional spaeter:

- Warnung plus Skip-Modus per Flag

Beispiel:

```text
--skip-mismatched-source-id
```

Dann ist das Verhalten bewusst und explizit.

## 5.4 Zukuenftiger Set-Builder

Empfohlener neuer Standard:

```powershell
python .\tools\effect_packager.py pack-effect-set .\my_set .\dist\my_set.lefxset
```

Dabei erwartet das Tool:

- `set.yaml`
- `commands.json`
- `effects/*.lefx`

Zusatzvalidierungen:

- jede `.lefx` ist fuer sich verifizierbar
- alle `source_id`s stimmen ueberein
- alle `qualified_effect_id`s sind eindeutig
- alle in `commands.json` referenzierten Effekte existieren
- kein Command referenziert einen Effekt anderer Quelle

## 6. Vorschlag fuer die naechste CLI-Ausbaustufe

Ich wuerde das Tooling fuer die naechste Stufe so schneiden:

## 6.1 Single-Effect-Workflow

Neue Befehle:

- `init-effect`
- `validate-effect-source`
- `pack-effect`
- `pack-effect-batch`

### `init-effect`

Erzeugt Geruest fuer einen einzelnen Effekt.

### `validate-effect-source`

Prueft einen Effektordner vor dem Packen.

### `pack-effect`

Baut genau einen Effektordner zu einer `.lefx`.

### `pack-effect-batch`

Liest eine JSON-Datei mit mehreren Effektdefinitionen und erzeugt daraus mehrere Effektordner oder `.lefx`-Dateien.

## 6.2 Effect-Set-Workflow

Neue oder angepasste Befehle:

- `init-effect-set`
- `validate-effect-set-source`
- `pack-effect-set`

### `init-effect-set`

Erzeugt:

- `set.yaml`
- `commands.json`
- `effects/`

### `validate-effect-set-source`

Prueft:

- Struktur
- vorhandene `.lefx`
- passende `source_id`
- valide Commands

### `pack-effect-set`

Packt ein Set ausschliesslich aus vorhandenen `.lefx`.

## 7. Konkrete Weiterentwicklung des Authoring-Formats

## 7.1 Empfohlener Standard fuer Einzeleffekte

Ich wuerde fuer Menschen diesen Standard setzen:

```text
my_effect/
  effect.yaml
  effect.py
  assets/
  extra/
```

## 7.2 Empfohlener Standard fuer Sets

```text
my_set/
  set.yaml
  commands.json
  effects/
    one.lefx
    two.lefx
    three.lefx
```

## 7.3 Batch-Datei fuer viele Effekte

Optional:

```text
effect-batch.json
```

Verwendung:

- Scaffold vieler Effektordner
- Build vieler `.lefx`

Nicht empfohlen als einziges dauerhaftes Pflegeformat fuer Menschen.

## 8. Mein konkreter Architekturvorschlag

Wenn wir diese Weiterentwicklung angehen, wuerde ich sie so ausrichten:

### Phase A: Authoring ergonomisch machen

- `init-effect`
- `init-effect-set`
- kommentierte YAML-Vorlagen
- saubere Validierungsbefehle

### Phase B: Single-Effect-Building erweitern

- Assets und extra Python-Dateien explizit dokumentieren
- Batch-JSON fuer Mehrfach-Scaffolding oder Mehrfach-Build

### Phase C: Set-Building haerten

- `.lefxset` nur noch aus gebauten `.lefx`
- `source_id`-Konsistenz hart pruefen
- Commands gegen reale `.lefx` validieren

### Phase D: Komfortverbesserungen

- optionaler Skip-Modus bei Mismatches
- Template-Varianten
- Batch-Erzeugung fuer Effektfamilien

## 9. Was ich unveraendert beibehalten wuerde

Ein paar Dinge wuerde ich trotz der neuen Ideen bewusst nicht aufweichen:

1. Python bleibt die eigentliche Renderlogik.
2. Ein `.lefx` bleibt die kleinste distributierbare Einheit.
3. Commands bleiben feste Befehle und keine frei parametrisierbaren Templates.
4. `qualified_effect_id = source_id::effect_id` bleibt bestehen.
5. Ein `.lefxset` repraesentiert weiterhin genau eine Quelle.

## 10. Meine kompakten Empfehlungen

Zusammengefasst wuerde ich deine Ideen so bewerten:

- `init-effect` mit automatisch erzeugtem Ordner, `effect.py` und `effect.yaml`: unbedingt machen
- Assets und zusaetzliche Python-Dateien: unbedingt erlauben
- kommentiertes YAML-Template: unbedingt machen
- JSON als alternatives Input-Format: ja
- mehrere Effekte in einer JSON-Datei: ja, aber eher fuer Batch-Workflows
- `.lefxset` nur aus bereits gebauten `.lefx`: sehr gute Idee, sollte Zielstandard werden
- `source_id`-Mismatch im Set-Build: nicht still skippen, sondern standardmaessig hart abbrechen

## 11. Vorschlag fuer die naechste Folgeentscheidung

Wenn wir das als naechsten Schritt umsetzen wollen, waeren aus meiner Sicht nur noch diese drei Detailentscheidungen noetig:

1. Soll `init-effect` nur YAML als Primärvorlage erzeugen oder YAML und JSON?
2. Soll `pack-effect-batch` aus einer JSON-Datei direkt `.lefx` bauen oder zuerst Effektordner scaffolden?
3. Soll der Set-Builder den heutigen Source-Dir-Modus sofort verlieren, oder wollen wir fuer eine Uebergangszeit beide Modi parallel unterstuetzen?

Mein bevorzugter Kurs waere:

1. YAML als Primärvorlage, JSON optional
2. Batch-JSON zuerst fuer Scaffold und optional spaeter fuer Direkt-Build
3. kurzer Uebergangsmodus mit Warnhinweis, danach Set-Build nur noch aus `.lefx`

Damit waere das Effect-Building die naechste saubere Ausbaustufe der bereits vorhandenen V1, ohne das bestehende Paketmodell wieder aufzubrechen.
