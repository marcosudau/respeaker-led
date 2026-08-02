# history_doc_led_controller_respeaker.md

1. - Neue Konzept-Idee + Erste Deployment / Release-Planung   [08__02]

2. - Finalisierung des Konzepts "Effekt-Dateien"  [08__03]

3. - Finalisierung II des Konzepts "Effekt-Dateien"  [08__04]

4. - Konkretisierung Effekt-Planung  + Allg. Sammlung weiterer Ideen

3. - Konkretisierung Effekt-Planung  + Allg. Sammlung weiterer Ideen











## Eine Effect-Engine vor einem Layer-System

- Die Engine soll die Hauptverantwortung haben für die Ausgabe der LED-Effekte 
- Alle anderen SteuerungsWege müssen strukturell dann eben vor der Engine angesiedelt ist. 
- Alle Wege sollen halt davor irgendwie gekapselt werden oder in der Engine müssten mehrere Möglichkeiten integriert werden.

- Wir sollten die Planung mittel- bis langfristig strategisch ausrichten, da wir ein so riesiges Vorhaben ohnehin nicht in einem Ruck umsetzen können..  
- Ich nehme an dass es wohl nur klappen wird, wenn wir mehrschrittig in Phasen planen...In der ersten Phase haben wir schon viel gewonnen wenn wir alle Komponenten vor die Engine bekommen damit nicht ständig diese Direktsteuerungen dazwischenfunken... 
- Und wenn wir auf notfalls auf biegen und brechen eine ganze Batterie an Adaptern vor die Engine hauen, damit jede erstmal noch Komponente Ihren Individualismus ausleben kann..
- Aber der Aufwand macht nur Sinn, wenn wir von Anfang an das einheitliche Schema festlegen damit wir, zumindest soweit es möglich ist, bei allem was wir tun schon in diese Richtung denken und hinarbeiten.


### Umstrukturierung / Neuausrichtung des led_controller

-Ich möchte mit dir hier eine Umstrukturierung / Neuausrichtung vornehmen, bei der das Prinzip eher als ein dauerhaft laufender Dienst ausgerichtet soll, statt nur für die Ausgabe einzelner konkreter Effekte...
- Bitte verschaffe dir einen Überblick über dieses Projekt..Lese dazu die Docs (insbesondere auch den Dev-Teil) und analysiere den Code... Das Ziel dabei ist es dass du das Projekt insgesamt verstehst und auch den genauen aktuellen Stand. Erst danach lese bitte den Rest meiner Nachricht ab hier.

- Erstelle eine md-Datei in der du eine ausführlichen Bericht zu dem geplanten Änderungen verfasst. Ich möchte daran erkennen können ob du denn Sinn und Zweck, sowie alles wesentlichen Informationen auf dem Schirm hast...  
- Anschliessend ergänze dort einen Abschnitt mit deiner Einschätzung, wichtigen Ergänzungen und weiteren Vorschlägen, sowie möglichen Stolperfallen und Problemen die wir beachten sollten...


### Engine 
- Die Effekte sollen alle nur über die vorhandene Engine ausgegeben werden, die sie in das Layer-System "einsortiert".
- Es soll keine Wege mehr an der Engine vorbei geben: Alle Eingabe-Formen (CLI, API, Adapter, Wrapper, ...) müssen vorher durch Preprocessing/Normalisierung vereinheitlicht werden...("übersetzt in die Sprache, die die Engine versteht")
- Zum Schluss mache einen Vorschlag, wie wir das Ganze angehen....


### Effekte
- Vereinheitlichung: Alle Effekte sollen durch ein einheitliches Grundschema definiert werden können, das von der Engine verarbeitet wird:
  - Das Grundschema könnte eine Kombination sein aus 
    - Python-Methode (für die Logik)
    - Nicht-Änderbare Eigenschaften (z.B. eindeutige id in snake_case, Layer-Einschränkungen,...) 
      -> Damit es überhaupt funktionieren kann, alle Effekte in einem einheitlichen Schema zu definieren, müssen die unterschiedlichen Anforderungen über feste, nicht änderbare Eigenschaften geregelt werden.
	  -> Beispiel: Auf den unteren beiden "State-" Layern werden Effekte für eine unbestimmte Dauer gesetzt, die solange laufen bis es geändert wird. Es muss also sichergestllt werden, dass nur Effekte die die Voraussetzungen erfüllen (entweder rein statisch oder Dauer-Loop-fähig) dort gesetzt werden können. Im Gegensatz dazu ist für die Effekte auf den anderen Layern ein einmaliges Abspielen vorgesehen.
	  -> Mögliche Lösung: In den Eigenschaften eines Effekts wird festgelegt, für welche Layer er unter welchen Bedingungen freigegeben ist...z.B. kann für die State-Layer die Voraussetzung duration=0 sein, da eine feste Dauer dort nicht passt... Mit festgelegter Dauer kann der selbe Effekt dann jedoch für die anderen Layer geeignet sein... 
    - Änderbare Eigenschaften (z.B. Farbe, Geschwindikeit, Dauer,...)
	  -> Variable Eigenschaften, mit denen die Darstellung der Effekte beeinflusst/konfiguriert werden kann.
	  -> Die Angabe der variablen Eigenschaften soll IMMER nur optional sein, deswegen MUSS für jede ein Default-Wert in denNicht-Änderbaren Eigenschaften hinterlegt sein..
      -> z.B. Farbe, Geschwindikeit, Dauer, transparenz(Bool der festlegt, ob bei ungenutzten LED's der Effekt des Layers darunter durchscheinen darf)...


### Layer
- Die Engine selbst soll Bedeutungsneutral sein, deshalb muss u.A. die bisherige Benennung der Layer geändert werden. (Auflistung der Layer mit Beschreibung/Priorität erkläre Ich weiter unten)
- Das Layer-System stellt immer die aktuelle Ausgabe dar und regelt die Priorisierung/ Überlagerung von Effekten.
- Der Composer baut erstellt aus den Layern von unten nach oben die aktuelle Scene, die vom Renderer gerendert wird. (Prinzip in 'docs\dev\runtime_layers.md' beschrieben) 
- In jedem Layer kann zur selben Zeit immer nur 1 Effekt gesetzt sein. Setzten einen neuen Effekts überschreibt vorherigen. Anzeige kann mit enabled-Bool temporär (de-) aktiviert werden, der gesetzte Effekt bleibt dabei erhalten.


#### BACKGROUND_STATE_LAYER
- BACKGROUND_STATE_LAYER_PRIORITY = 100
- Dieser Layer stellt die unterste Ebene und damit den Idle-State dar. Dieser Layer ist primär für den "Ruhe- bzw. Standby-Zustand" gedacht, solange keine Anwendung etwas gesetzt hat...
- Besonderheit: Der hier gesetzte Zustand wird immer persistent in einer Datei gespeichert, die bei allen Änderungen aktualisiert wird und bei start/neustart wird die Datei gelesen um den eingestellten Effekt wieder setzten zu können. (Fallback: Falls keine Datei gefunden wird -> alle LED's off... Sobald dann etwas geändert/gesetzt wird->Datei wird erstellt)   
- Beispiel: mit geringer Helligkeit, statisch oder leicht pulsierend

#### STATE_LAYER
- STATE_LAYER_PRIORITY = 200
- Dieser Layer ist dazu gedacht,dass die Anwendungen die den Service nutzen einen Zustand darstellen. 
	
#### MAIN_LAYER
- MAIN_LAYER_PRIORITY = 300
- Haupt-Effekt... Hier habe ich an keinen speziellen UseCase gedacht... Anwendungen können sich hier kreativ austoben..

#### TEMP_OVERLAY_LAYER
- TEMP_OVERLAY_LAYER_PRIORITY = 400
- Layer für Zeitlich begrenzte Effekte, die temporär als Overlay über den Haupteffekt/State gelegt werden sollen
- Beispiele dafür könnten sein z.B. Timer- oder Fortschrittsanzeigen sein, die bis zu ihrem Abschluss übergelegt werden..

#### ONGOING_OVERLAY_LAYER
- ONGOING_OVERLAY_LAYER_PRIORITY = 500
- Layer für Zeitlich unbegrenzte Effekte, die temporär als Overlay über die unteren Layer gelegt werden.
- Beispiele dafür könnten sein z.B. Eine DoA-Anzeige, die bei erkannten Geräuschen mit einer LED die Richtung anzeigt... Sie könnte mit transparent=true so konfiguriert werden, dass sie bis auf die eine LED die restliche Anzeige nicht beeinträchtigt.
	
#### EVENT_LAYER
- EVENT_LAYER_PRIORITY = 600
- Kurze Effekte mit höchster Priorität...Könnte kurzes aufblitzen oder rotieren sein.
- Falls mehrere in kurzer Zeit gesetzt werden, werden diese in einer Warteschlange nacheinander angezeigt.
- Gedacht zum signalisieren kurzer Benachrichtigungen, wie Fehler, Warnungen,etc...



## Neue Konzept-Idee für Effekte + Erste Deployment / Release-Planung

- So, was wir jetzt machen, ist rein hypothetisch. Deshalb möchte ich, dass du keine Änderungen an Code oder an der Dokumentation vornimmst, ausser eine einzige Markdown-Datei zu erstellen, in der du am besten ausformulierst, was wir jetzt besprechen. 
Und zwar habe ich die Vorstellung, 

("08__02_konzept_effekt_dateien.md", "08__03_konzept_effekt_dateien.md", "08__04_konzept_effekt_dateien.md")

### Konzept/Idee "Effekt-Dateien"
- Effekt-Dateien (Neuen Dateityp, könnte man sich ausdenken.) 
  - Enthalten immer einen einzelnen konkreten Effekt.
  - Sollen komplett unabhängig sein von builtin effekten usw...
  - Sollen wie eine Art Komplett-Paket sein, in das alles gepackt wird was gebraucht wird um komplett unabhängig und für sich eigenständig zu sein, z.B.:
    - die Definition 
    - Renderlogik
    - festgelegte Parameter-Werte (id, Farbe, Layer, ggfs. Dauer, Helligkeit,etc..)
  - Wenn die Dateien einmal gebaut wurden soll der Inhalt nichtmehr lesbar oder änderbar sein..
  - Die meisten Anwendung werden mit einer handvoll Effekten arbeiten. Dieses Konzept soll dies vereinfachen indem die konkreten Effekte vordefiniert werden, sodass in den Anwendungen die Logik klein gehalten wird und sich nicht mehr um parameter etc kümmern muss, sondern dort nur sehr simple der befehl bekannt ist...
  - Der Namen/ Befehl zum auslösen eines bestimmten Effektes kann von der Anwendung entsprechend ihres Kontextes in dem der Befehl verwendet wird definiert werden.

  - Was wir vermutlich brauchen:
    - Neuen Befehl, mit dem die Anwendung dann nach starten des Service den Dateipfad oder Ordnerpfad(Autodiscovery) zum registrieren eingibt.. Und so Ihre eigenes Set an Effekten "mitbringt"
    - Neues Modul, zum entpacken, verarbeiten dieser Dateien, um sie in der Instanz für die aktuelle Laufzeit zu registrieren
    - Kleines, komplett unabhängiges cli-tool zum erstellen dieser Dateien/ Packaging..
 
- Effekt-Set-Dateien (Könnte man sich einen seperaten neuen Dateityp ausdenken) 
  - Sind so etwas wie ein Container für mehrere einzelne Effekt-Dateien...  
  - Könnte ebenfalls mit einem unabhängigen cli-tool erstellt werden, dass aus mehreren Effekt-Dateien eine Effekt-Set-Datei zusammen packen kann...
  - Beispiel: Eine Effekt-Set-Datei könnte 6 States, 3 Main-Effekte, jeweils 2 Ongoing/temp-Overlay-Effekte und 5 unterschiedliche Event-Effekte enthalten...

Wie schätzt du das ein? Was hältst du von der Idee?
Was für ein Konzept könntest du dir vorstellen, um das möglichst effizient zu integrieren? 
Auf welche Arten könnte man diese Dateien/ den Inhalt gestalten um alles zusammen zu packen? 
Hättest du ergänzende Ideen oder Verbesserungsvorschläge dazu?


### Deployment
- Ich möchte langsam anfangen, das Deployment/Build des LED-Controller nachzudenken um jetzt rasch zu einer ersten release-version zu kommen...
- Ich habe 2 unterschiedliche Arten, wie der led_controller verwendet werden soll...
  - 1. Kurzfristig für die ersten Release-Versionen: Wird als Unterprozess von der Anwendung gestartet, die ihn benutzen möchte...
  - 2. Das ist der mittel- bis langfristige Plan wom es hingehen soll, noch nicht für die ersten Release-Versionen: Als installierter, dauerhaft laufender, eigenständiger Windows-Dienst. Der alles hat was ein typischer Windows-Dienst so mitbringt...Also auch in Windows unter DIenste erschint, wenn er beendet wird automatisch neu startet, usw...

-Was würde uns effektiv noch für die erste Release-Version fehlen? 
- Wie schätzt du die beiden Arten ein der Verwendung, die ich eben erwähnte? 
- Wie würde das Auslieferungs- beziehungsweise Distributionsformat aussehen und wie wäre ein möglicher build-prozess? 
- Worauf sollten wir zuzdem noch achten?

Bitte erstelle eine Markdown-Datei, in der du einmal das komplette Konzept dafür entwirfst und auch alle konkreten Schritte, die wir jetzt noch dafür gehen müssten, ausführst.
Das ist uch noch Teil der Planung und du solltest dazu noch nichts ändern....


### Infos zur Release 1 vorbereitung
- Wir konzentrieren uns jetzt erstmal auf das Modell mit dem Unterprozess und lassen den Windows-Dienst erstmal komplett aussen vor, um uns auf Release-Version 1 zu konzentrieren.

- Als Release-Format würde ich gerne eine Windows-Exe erstellen, in der alles enthalten ist, also auch Python, damit keine zusätzlichen Abhängigkeiten entstehen und sie auf jedem System verwendet werden kann. 

- Als nächstes bitte ich dich, eine Fehlerbehandlung und ein einfaches Loggingsystem konsistent und releasetauglich zu implementieren, ohne das es viel aufwand ist und möglichst geringem Riiko das es dadurch zu Fehlern oder SideEffecte kommt...Also wirklich nur ganz simples Basic- / Minimalsystem..  

- Ich würde sagen, dass die Host-Anwendung den Port schon selber setzen kann, zumindest optional... Wir sollten dennoch bei unserem Standardport als Normalfall bleiben...

- Wir sollten definitiv eine Überprüfung vorher durchführen, ob der Port verfügbar ist oder bereits verwendet wird.

- Als Alternativen könnten wir einen gewissen Pool an Ports festzulegen... Wenn ein Port belegt ist soll aus diesem Pool ein anderer Port genommen werden... Aber das müsste ja dann irgendwie an die Host-Anwendung zurückgemeldet werden, hast du eine Lösung wie man das hinbekommt?

- Um bei der LED-Anzeige nicht in Konflikte zu geraten, sollten wir nur eine Instanz zulassen. Dabei sollte eine neu gestartete Instanz Vorrang haben und die alte beendet werden. Es wäre gut, wenn du dir da etwas einfallen lässt, wie wir das hinbekommen.
  -Zusatz: Um den Start/Stop des Service auf dem Gerät anzuzeigen sollen,  die LEDs dreinmal schnell hinztereinander aufblitzen... Beim Start in Grün und beim Beenden in Rot....Bitte jetzt sofort Implementieren... und durch tests bestätigen dass es erfolgreich implementiert wurde und alles funktioniert... 

- Ob das Gerät angesschlossen ist oder nicht werden wir später eine Prüfung hinzufügen, nach Release 1... Erstmal gehen wir davon noch aus, dass es angeschlossen ist...

- So, jetzt bitte ich dich, den finalen Vorbereitungsschritt zu machen, sodass wir danach zur Release-Version kommen können. Dazu bitte alles einmal so implementieren aus, ich denke, du hast jetzt genug Informationen von mir bekommen, wie das Ganze werden soll, und natürlich auch testen und überprüfen, dass alles fehlerfrei funktioniert.  

- Wenn es noch irgendwelche offenen Punkte gibt, dann schreib sie mir. Aber ansonsten möchte ich, dass wir gleich zur Release-Version kommen. Du kannst mir in der nächsten Nachricht dann auch erstmal den konkreten Ablauf des Bildprozesses und so weiter beschreiben. Also alles vorbereitende unternehmen, dass wir danach in dem Schritt den Build durchführen können.


### Background-State
Ist zwar nur eine Kleinigkeit, aber bitte kümmere dich mal eben darum... Dafür darfst du natürlich Änderungen vornehmen...:
- Persistentes speichern in einer Datei, wiederherstellung bei Service-Start
- Fallback ändern: Um am Gerät anzuzeigen, dass der Service online ist, soll Background-State-Fallback nichtmehr "off" sein, sondern als default "solid" in weiss "#FFFFFF" mit Helligkeit "0.2"
- In doc aktualisieren..


## Finalisierung des Konzepts "Effekt-Dateien"

### Meine Anmerkungen zu "08__02_konzept_effekt_dateien.md"

- Die ursprüngliche Idee, dass die fertigen Dateien eine Art Verschlüsselung oder sonstige Geheimhaltungsmechnismen erhalten, wird verworfen. Trotzdem sollte die Integritaet der Dateien sichergestellt sein.

- Die Ausführungen haben mich überzeugt, dass wir als Distributionsformate `.lefx` fuer einen Effekt und `.lefxset` fuer ein Effektset in Form von einem  signierten ZIP-basierten Containerformats mit klarer Struktur festlegen sollten.

- Von den vorgestellten Varianten hat mich "Variante A: Gepackte Python-Effektdatei" insgesamt überzeugt, da ich es für wichtig halte, dass auch aufwendige Effekte mit indiividueller Python-Logik möglich bleiben sollen.

- Alle Verbesserungsvorschläge sollten umgesetzt und deshalb im finalen Konzept mitgedacht werden... also A,B,C,D und E

### Folgeanweisungen

- Bitte arbeite das Konzept einmal komplett final aus und erstelle ein schlüssigen Gesamtentwurf. 
- Erstelle auch schon einen konkreten Implementierungsplan. Dieser sollte die gesamte Implementierung umfassen und sie in sinnvolle,einzeln testbare Teilabschnitte aufteilen die klar definiert werden.
- Verfasse in einer Folge-md-Datei eine ausführliche Gesamt-Darstellung des Finalen Konzepts
  - Ein Abschnitt, in dem alles formsle zu dem Konzept in Bezug auf Dateien, Format, Aufbau, was ist in den Dateien, Dev- und Distributionsformat, Schema usw. erläutert wird
  - Ein Abschnitt, der Implementierung in bestehende Logik thematisiert.. Also wie genau wird es von der Architektur her hinzugefügt, welche Eingriffe/Änderungen sind notwendig.
  - Übersichten zu wichtigen Teilen, wie API und CLI-Entwurf für Registrierung, Discovery und Befehlsaufruf. 
  - Die Einteilung der weiteren Abschnitte darfst du frei entscheiden, je nachdem was in dem finalen Konzept relevant ist.
  - Sollten noch entscheidungen von mir erforderlich sein füge sie am Ende übersichtlich und kompakt an. 
  
Es sollte soweit ausgearbeitet sein, dass ich dnn nur noch grünes Licht geben oder letzte Entscheidungsfragen beantworten brauche,  damit du es anschcliessend im darauf folgenden Schritt komplett Implementieren/ umsetzten kannst. 
- Da das Konzept und die Idee erstmal noch experimentell sind, wird daran nur ausschließlich auf dem seperaten Branch "codex/effekt-dateien"


- Bitte lese dir den erlauf zu dem Konzept in "docs\planning\konzept_effekt_dateien\" durch, um das Vorhaben zu Verstehen und den bisherigen Planungsverlauf nachvollziehen zu können...  
Die aktuellen Folgeanweisungen findest du in der Datei "08__03_konzept_effekt_dateien.md".
- Bitte erstelle das finale Gesamtkonzept nach diesen Folgeanweisungen... 


## Finalisierung II des Konzepts "Effekt-Dateien"

### API-Routen

- Meine Anmerkungen zu "08_04_konzept_effekt_dateien.md"

- Zu commands.json habe Ich noch Fragen...
  - So wie Ich es sehe, werden die Befehle nur dort benannt, aber das müsste doch in den  die Einzel-befehlen festgelegt sein, oder wie funktionieren die?
  - Ebenso wundert mich, dass dort parameter angegeben werden (color, duration) weil die Einzel-befehle doch eigentlich auf parameter festgelegt sind??
  - Vielleicht verstehe ich das auch nicht richtig, dann korrigiere mich, aber eigentlich müsste das doch pro einzelnen befehl fest sein...  

- Zur API:
  - Du hast zur Registrierung diese Routen "POST /api/v1/effect-sources/register-package" und "POST /api/v1/effect-sources/register-set" angegeben...
  - Könnte man nicht besser nur "POST /api/v1/effect-sources/register" machen um es nach aussen einfacher zu machen, und dann intern unterscheiden... z.B. anhand des Dateiformats?
  - Gleiches dann natürlich auch bei cli
- Auch bei deinem Beispielbefehlsaufruf (kopiere Ich dir nochmal, dmit du weisst welchen ich meine) wurde der Parameter "color" mit angegeben... Das sollte doch eigentlich unmöglich sein, da ein registrierter befehl eine feste farbe hat.. Einer der wichtigsten Gründe ist ja, das die Anwendungen nichts mehr mit parametern zu tun haben, sondern nurnoch mit den befehlen... Also müssten für den selben effekt in anderer farbe ein seperater befehl angelegt sein...
{
  "command_name": "listening",
  "source_id": "app.voice_assistant",
  "payload": {
    "color": "#55CCFF"
  },
  "replace_existing": true
}
- Bei dem Befehlsaufruf könnte man 
- Bei dem Befehlsaufruf könnte man "replace_existing" weglassen, weil es ohnehin immer true sein muss, sonst bräuchte man den Befehl garnicht aufrufen...Und wenn im einzelbefehl die parmeter ohnehin fest sind, braucht man auch payload nicht...
- Wie findest du die Idee, bei der Registrierung eigene API-Routen anzulegen für source und jeden command, z.B:
  - "POST /api/v1/commands/voice_assistant"
    - Auflistung aller Befehle, die zu dieser Quelle registriert sind.
  - "POST /api/v1/commands/voice_assistant/listening"
    - Wenn nicht gesetzt: Setzt den Effekt im Layer(on), Ansonsten: togglet zwischen on und off
  - "POST /api/v1/commands/voice_assistant/listening/on"
    - es wird sichergestellt, das der effekt unabhängig vom aktuellen status, auf "on" gesetzt wird
  - "POST /api/v1/commands/voice_assistant/listening/off"
    - es wird sichergestellt, das der effekt unabhängig vom aktuellen status, auf "off" gesetzt wird
- Dadurch könnte man die Route "POST /api/v1/effect-commands" ganz sparen, weil man es mit in "/api/v1/commands" hat
- Die Route "POST /api/v1/effect-sources" kann bleiben wie du sie vorgeschlagen hast...


### Aufräumen / Neue Ordnerstruktur....
- Ich finde, dass das Projekt mittlerweile recht gross wird, und durch die vielen Dateien auch langsam unübersichtlich... 
- Insbesondere im Ordner src sind mittlerweile sehr viele Module..
- Könntest du dort bitte eine neue Struktur mit Unterordnern im Ordner src anlegen, in die die Module nochmal sinnvoll eingeordnet werden? 
- Ich habe bei solchen Umstrukturierungen immer die Sorge, dass es zu einem Chaos bzgl. der Referenzierungen führt... 
- Sollten wir die Modulnamen deshalb besser Projektweit verfügbar machen? Entscheide selbst, ob du das für sinnvoll hälst...
- Die Ordner python_control und led_effects gehören fachlich eigentlich auch eher mit in den Ordner src, bitte verschiebe Sie dorthin...
- Anschliessend stelle durch tests, manuelle Überprüfungen und Ausführungen sicher, dass alles funktioniert und es keine Fehler gibt.
- Stelle auch sicher, dass in allen übrigen Dateien (wie z.B. Doc- oder Builddateien) überall die richtigen neuen Pfade verwendet werden und an keiner Stelle im gesamten Projekt noch ein lter/falscher Pfad verwendet wird.


### Zu deinen noffenen Fragen...
1. Die strikte Release-Pruefung ist erstmal unwichtig, lass uns die auf später irgendwann verschieben um uns erstmal darauf zu konzentrieren, eine funktionierende Grund-Version zu erstellen.
2. Ja, das vorgeschlagene Schema ist gut, das nehmen wird...
3. Nein, nicht persistent speichern.. Zumindest nicht über "effect_sources.json"... Wenn die Dateien in dem Autodiscovery-Ordner liegen sollen sie aber erkannt und geladen werden..
4. Es reicht zuerst nur pack, inspect und verify ... (auch wegen Fokus auf funktionierende Grund-Version)
5. Von Anfang an nur mit .lefx und .lefxset arbeiten...



## Konkretisierung Effekt-Planung  + Allg. Sammlung weiterer Ideen


- DoA Integration und Template
- Idee: Config-Unterstützung + Logging auf weitere Bereiche erweitern
- Idee: Farben-Namen als Enums
- Idee: Farben-Namen als Enums
- PySide6-Test-App - Probleme fixen
- PySide6-Test-App erweitern Richtung Live-UI/Effekt-Studio
- Building der `.lefx` und `.lefxset`-Dateien allgemeiner fassen (nicht nur default-Pakete)


("08_11_konzept_effekt_dateien.md", "08_12_konzept_effekt_dateien.md")

### DoA Integration und Template

Super, vielen Dank. Schau dir einmal das neue System an. Bei den Effekten hat sich einiges getan. 
Und ja, es gibt jetzt ein neues System, wo quasi Effekte vorgebaut werden. Sodass du da einmal auf dem aktuellen Stand bist. 

Danach möchte ich, dass du in "docs\planning" die Datei "11_konzept_DoA_integration_und_template.md" erstellst und darin ein Konzept ausarbeitest zur Integration und Nutzung der tatsächlichen DoA-Werte, die der respeaker erkennt. 

### Info's
- Ziel ist ein wiederverwendbares Effect-Template, dass bereits die komplette Logik beinhaltet, um die LEDs nach der Richtung von der erkannten Sprache zu sezten.
- Das Template sollte zu unserem aktuellen Effekte-System passen und kompatibel sein.
- Die Integration sollte nicht einfach an allem vorbei im Alleingang erfolgen, sondern möglichst an bestehende Prinzipien und Strukturen anknüpfen.
- Hinweis: es sollte nicht der in dem ReSpeaker eingebaute Standard-Doa-Effekt benutzt werden, sondern es soll eine eigene Logik gestellt werden.
- Ein Allgemeines Beispiel wie diese generell vom ReSpeaker abgefragt werden  ist in "src\python_control\respeaker_get_doa.py".
- Du kannst dich an dem Beispiel orientieren, solltest es jedoch nicht so übernehmen... Wir brauchen eine spezifische Lösung für unseren Anwendungsfall..

### Architektur-Fragen
Aus deinem Konzeptentwurf sollten folgende Fragen auch auf jeden Fall mit beantwortet werden:
- Wie genau empfiehlst du die Integration in den bestehenden Code? 
- Muss für die Logik ein eigener Unterprozess laufen, damit sie durchgehend funktioniert? 
- Inwiefern besteht das Risiko von Konflikten parallel ausgeführter Effekte der Engine? 
- Sollte der ReSpeakerAdapter um eine Methode zur Abfrage der DoA-Werte erweitert werden?
- Wie genau sollte die aktulisierung erfolgen und wie oft?

### Zielvorgaben
Die Logik sollte bei den LEDs zwischen drei verschiedenen Bereichen unterscheiden, für die jeweils Eigenschaften festgelegt werden können:
- 1. "direction_led": die eine LED, die in die Richtung von erkanntem Sound / Sprache zeigt. (default=grün)
- 2. "wing_leds": wing_leds werden wie "Flügel" neben der direction_led hinzugefügt, sodass auch mehrere LEDs in die Richtung zeigen können.(default=weiss) 
     - Sie sollen optional über einen int-Parameter aktiviert werden können, Der Wert  0 bedeutet es gibt keine wing_leds, der Wert  1 bedeutet, dass neben der Direction LED an jeder Seite 1 LED als wing_led hinzugefügt wird, usw...
     - Die Eigenschaften (Farbe, Helligkeit, etc) der wing_leds sollen unabhängig festgelegt werden können, sodass sie sich auch von denen der direction_led unterscheiden können.
- 3. "background": Oder einfach: Der Rest... gemeint sind damit alle Leds, die weder direction_led noch wing_leds sind. Im Normalfall werden diese leds einfach nicht gesetzt/bleiben aus... Es soll trotzdem die Möglichkeit bestehen eine Hintergrundfarbe zu setzen(default=None)

Zudem soll zwischen diesen Zuständen unterschieden werden können:
- 1. Keine Erkennung: Es wurde kein Geräusch erkannt, keine Richtungsangabe
- 2. Geräusch Erkannt: Es wurde ein Geräusch erkannt und die Richtung kann angegeben werden.
- 3. Sprache Erkannt: Genau wie beim Geräusch, nur dass zusätzlich erkannt wurde, dass es sich um Sprache handelt. Das wird in der Doa-Abfrage als Wert mit angegeben und kann genutzt werden.

Also theoretisch sollte es möglich sein, Für jede Kombination aus Bereich und Zustand seperat die Eigenschaften festzulegen... Da das jedoch nur selten erforderlich ist, sollen die angaben nur optional nach bedarf gemacht werden können .. Fallback auf default-Werte
-> Um zu demonstrieren dass es auch funktioniert wie es soll, erstelle aus dem Template den folgenden konkreten Effekt:
   

### PySide6-Test-App - Probleme fixenPySide6-Test-App 
- Overlay-Effekte können nicht abgespielt werden und werfen die Fehlermeldung "finite duration required"
- Es werden nicht immer bei allen Effekten die widgets für alle parameter hinzugefügt... Bitte teste und debugge das, indem du die anzahl der parameter mit den tatsächlichen Layout-Einträgen abgleichst. Bitte vollständig testen und nicht nur exemplarisch... also für jeden einzelnen Effekt überprüfen ob für alle parameter einträge im Layout erstellt werden..


### PySide6-Test-App erweitern Richtung Live-UI/Effekt-Studio
- Die PySide App bietet in ihrem aktuellen Stand gerade mal grobe Funktionalität, obwohl ich da deutlich mehr Potenzial sehe. 
- Ein  deutlicher Vorteil für die Praxis wäre es, Über die Gui mit komfortablem Widgets die Parameter (z.B. für Presets) zu konfigurieren, während man sich den Effekt dabei live auf dem Gerät anschauen und etwas mit den Werten herumprobieren kann...
- kleine Anpassungen:
  -  Einen checkable-Button hinzufügen zum aktivieren der Loop-Wiedergabe Für alle Effekte die eine begrenzte Dauer haben. Solange der Button Checked ist, sollen diese einmalig-laufenden Effekte als Daerschleife im Loop abgespielt werden. Nach dem Abspielen soll dann eine kurze Pause mit konfigurierbarer Dauer angehngen werden. 
  -  Effekte sollen nichtmehr über ein Dropdown ausgewählt werden, sondern übersichtlich in einem Listview, dss wie eine Sidebar auf der linken Seite des Hauptinhaltsbereichs hinzugefügt wird...
  -  Textfeld, in dem immer die aktuelle konfiguration als fertiger und formatierter json-string steht und bei jeder änderung automatisch aktualisiert wirdsodass man ihn  dort kopieren und direkt in einer preset-datei einfügen kann...
Gerade auch wenn es darum geht,
vorzukonfigurieren
, man könnte dann automatisch die JSON-Dateien erstellen, mit den Parametern



### Idee: Config-Unterstützung + Logging auf weitere Bereiche erweitern
- Unterstützung für eine optionale config.json 
- bei start des service kann gecheckt werden ob config.json vorhanden ist (soll nicht required sein, nur nach dem Prinzip "wenn vorhanden dann ja", gilt genauso für alle einträge darin)
- "config.json" soll read-only sein
-
- Mit Blick auf Release-Version soll das Verzeichnis "runtime_state" zukünftig nichtmehr verwendet werden...
  - "active_service.json" soll stattdessen im System-/User- Temp-verzeichnis erstellt werden
  - "background_state.json" soll stattdessen nichtmehr gespeichert werden, sondern nur noch optional aus "config.json" gelesen werden
- Logging-Erweiterung
  - Das Logging soll erweitert werden, indem es in "config.json" für einzelne Bereiche (de-)aktiviert werden kann. (Wenn nicht angegeben: default=false)
- Beispielsweise könnte dort festgelegt werden:
  - Einzubindende Effekte (Als Pfad-Liste -Dateipfade zu \*.lefx- / \*.lefxset-Dateien; -Ordnerpfaden für Auto-Discovery;)
  - Background-State (wie aktuell in background_state.json)


```json
{
  "background_state": {
	"effect_id": "rotating_segment",
	"enabled": true,
	"layer_id": "BACKGROUND_STATE_LAYER",
	"params": {
	  "color": "FFFFFF",
	  "brightness": 0.2,
	  "speed": 9,
	  "segment_length": 3
	},
  },
  "logging": {
	"log_file": "P:\\CodexApp\\led_controller_respeaker\\logs\\led_controller.log",
    "engine_commands": true,
    "api_calls": true,
    "service_controller": true,
    "weitere...": true
  },
  "effect-discovery": [
	"P:\CodexApp\led_controller_respeaker\build\live_effect_package_smoke\demo_effect1.lefx",
	"P:\CodexApp\led_controller_respeaker\build\live_effect_package_smoke\live_demo.lefxset",
	"P:\CodexApp\led_controller_respeaker\build\live_effect_package_smoke"
  ]
}
```



### Idee: Farben-Namen als Enums
- Für die wichtigen Haupt-Farben die Verwendung der Namen hinzufügen, sodass diese für Eingaben und Ausgaben unterstützt werden.
- Bei Ausgaben wird vorher überprüft, ob es zu den jeweiligen Hex/RGB-Codes einen definierten Namen gint-> Wenn ja wird dieser in der Ausgabe verwendet
- Bei Eingaben genau umgekehrt...  


-Beispiel:

@dataclass(frozen=True)

class Colors:
    BLACK = RGB(0, 0, 0)
    WHITE = RGB(255, 255, 255)

    RED = RGB(255, 0, 0)
    GREEN = RGB(0, 255, 0)
    BLUE = RGB(0, 90, 255)
    CYAN = RGB(0, 220, 255)
    YELLOW = RGB(255, 180, 0)
    ORANGE = RGB(255, 100, 0)
    PURPLE = RGB(180, 0, 255)
    PINK = RGB(255, 0, 150)

    SOFT_GREEN = RGB(0, 160, 60)
    SOFT_BLUE = RGB(0, 100, 180)
    SOFT_CYAN = RGB(0, 140, 180)
    SOFT_RED = RGB(180, 0, 0)
    SOFT_YELLOW = RGB(180, 120, 0)
    SOFT_PURPLE = RGB(110, 0, 160)
 
class RGB:
    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        for value in (self.r, self.g, self.b):
            if not 0 <= value <= 255:
                raise ValueError("RGB values must be in range 0..255")

    def to_xvf_hex(self) -> str:
        return f"0x{self.r:02X}{self.g:02X}{self.b:02X}"

    def scaled(self, factor: float) -> "RGB":
        factor = max(0.0, min(1.0, factor))
        return RGB(
            int(self.r * factor),
            int(self.g * factor),
            int(self.b * factor),
        )

    def blend(self, other: "RGB", ratio: float) -> "RGB":
        ratio = max(0.0, min(1.0, ratio))
        inv = 1.0 - ratio
        return RGB(
            int(self.r * inv + other.r * ratio),
            int(self.g * inv + other.g * ratio),
            int(self.b * inv + other.b * ratio),
        )
		
		
		

### Effect-Building
- Meine Ideen zum Effect-Building, bitte erstelle zunächst 
- Lass uns im nächsten Schritt das Effect-Building weiter spezifizieren.


#### single-effect (*.lefx)
- Tool, zum erstellen von einzelnen \*.lefx-Dateien 
- Ordner, effect.py und effect.yaml werden automatisch erstellt
- Angabe von Assets / Py-Dateien wird unterstützt für zusätzliche Logik
- Unterstützt die Definition von Effekten durch ausgefüllte yaml/json 
- Kommentiertes yaml/json-Template wird als Vorlage erstellt.
- In einer json können mehrere Effekte hintereinander definiert werden-> jeweils eine eigene \*.lefx-Datei
- Validiert, dass alle benötigten Angaben vorhanden und schlüssig sind.

#### effect-set (*.lefxset)
- Tool, das mehrere \*.lefx-Dateien in eine \*.lefxset-Datei zusammenpackt
- Zwischenschritt über einzelne \*.lefx-Dateien immer erforderlich...
- source-id muss übereinstimmen... sonst wird Datei übersprungen und nicht mit aufgenommen


Da Presets bisher zwar angelegt waren, effektiv doch nicht ein einziges Mal benutzt wurden, würde ich vorschlagen dass wir um Verwirrung zu vermeiden, das alte Konzept erstmal komplett abbauen bzw. rausnehmen... 
Also sowohl im Code als auch in der Docu es komplett und sauber entfernen. Dann brauchen wir auch nicht auf Abwärtskompatibilität zu achten.
Deine 3-Ebenen-Einteilung finde Ich super, also die Aufteilung in:
- dem parametrisierbaren Effekt
- dem benannten Preset
- dem festen Command

Ich würde es jedoch nicht in der lefxset-Datei festlegen, sondern bereits in der einzelnen lefx-Datei. So bleiben diese als einzelne Effekte unabhängig vom Set verwendbar, und ein Set bleibt weiterhin nur die Zusammenfassung von mehreren... 
Beispielsweise enthält die Datei dann den eigentlichen parametrisierbaren Effekt, für den darin einige presets mit den häufig verwendeten Einstellungen vorhanden sind.
Für die Presets könnten wir als Namenskonvention festlegen, dass sie beginnen mit "state_", "effect_", "overlay_" oder "event_"... Je nachdem auf welchen Layer sie festgelegt wurden...
die commands könnten dann ebenfalls in der lefx-Datei definiert werden und wie du vorgeschlagen hast als Trigger für die presets verwendet werden. 
Zusätzlich könnte man aber auch noch einige commands definieren, mit denen (entweder manuell oder für übersichtlichere list-abfragen) Standard-Informationen abgerufen werden können...
Als Beispiel für den Effekt "soft_pulsing_ring":
- "soft_pulsing_ring.title" -Zum Abrufen des Titels
- "soft_pulsing_ring.description" -Zum Abrufen der Beschreibung
- "soft_pulsing_ring.params" -Zum Abrufen einer Liste mit allen unterstützten Parametern
- "soft_pulsing_ring.presets" -Zum Abrufen einer Liste mit allen Presets, untergliedert nach "states", "effects", "overlays" und "events" (Evtl auch einzeln abrufbar über "soft_pulsing_ring.states", usw...)
- "soft_pulsing_ring.commands" -Zum Abrufen einer Liste mit allen Commands, 
- "soft_pulsing_ring.info" -Zum Abrufen einer übersicht mit allen zuvor genannten infos...
- "soft_pulsing_ring.set" -Zum setzen des Effekts mit freier Parameterangabe.. (Bei nicht gesetzten Fallback auf default-Werte)

Was hälst du von diesem Vorschlag???

Ich hätte noch eine andere Sache die mich stört...
In  ring_effects.py ist es sehr unsauber gelöst, dass der Parameter "brightness" für alle gilt... 
Das sollten wir irgendwie besser/ allgemeingültiger lösen... 
Es wäre auch sinnvoll, bei effekten mit einer Helligkeitsspanne ("min_brightness"/"max_brightness") für den Maximalwert auch einfach nur "brightness" zu benutzen, damit wir diesen in einer allgemeinen Lösung mit ansprechen...
Ebenso würde mir dazu einfallen, dass der Parameter "speed" für alle animierten Effekte gültig ist

Ich möchte, dass wir das neue Gesamt-Konzept im nächsten Schritt festmachen, sodass es insgesamt rund und schlüssig ist und keine inkonsistenzen oder Behelfslösungen mehr aufweist. 
Dabei auch keine Rücksicht mehr auf Abwärtskompatibilität... Wenn wir eine Lösung haben die in sich rund ist, müssen wir das alte darauf anziehen... Soviel ist es ja noch nicht, dass es sich lohnen würde dafür sonderwege zu behalten...



Meine Anmerkungen findest du in "08_11_konzept_effekt_dateien.md"...


Okay, ich stimme all deinen Empfehlungen zu.
Eine kleine Anpassung hätte ich aber noch...
- Der Parameter "direction" wird aktuell meistens durch die enums "clockwise", "counterclockwise" festgelegt...
- Er soll umbenannt werden in "reverse" und als bool mit dem default-wert false festgelegt werden.
- Bitte überprüfe gründlich, dass die alte Bezeichnung "direction" nichtmehr dafür verwendet wird.
- Das hat folgenden Grund: 1. finde ich reverse bei Richtungsumkehr viel passender und 2. soll später noch eine Funktion zur DoA-Richtungserkennung von Sprache hinzugefügt werden, in der "direction" verwendet wird um per LED die Richtung anzuzeigen. Da dies eine komplett andere Bedeutung ist, soll es von Beginn an keine Möglichkeit der Verwechslung geben...

Da wir jetzt alles festgelegt haben für das Zielbild, bitte ich dich, nun um die vollständige Umsetzung In den von dir vorgeschlagenen Phasen bestätige dabei die vollständige und fehlerfreie Implementierung nach jeder Phase durch Tests. 
Nachdem alle Phasen erfolgreich umgesetzt wurden, überprüfe das Ganze nochmal auf Schwachstellen und Inkonsistenzen, um diese dann gegebenenfalls auch noch zu beheben. 
Stelle sicher, dass wir einen absolut in sich runden Stand haben, bei dem keine offenen Punkte mehr bestehen, sodass wir anschliessend den Branch in den Main mergen können.
Arbeite so lange weiter, bis alles abgeschlossen ist, und erstatte mir anschließend Bericht.


- Ist es sicher richtig, dass Dateien wie effect_preset_r?egistry.py oder effect_package_schema.py oder effect_package_builder.py oder effect_command_registry.py alle innerhalb des Ordners "src/engine" sind
Das kann Ich mir nicht so richtig vorstellen und habe Zweiffel daran... 
- Das korrekte Zielbild ist in 08__12_konzept_effekt_dateien.md richtig beschrieben, bitte nehme das als belastbare Grundlage. Ich habe Zweiffel daran, dass es so wie in 08__13_konzept_effekt_dateien.md dokumentiert wurde nicht ganz korrekt ist, deshalb überprüfe das bitte kritisch aber betrachte 08__13_konzept_effekt_dateien.md nicht als Quelle der Wahrheit...


- Entferne alles zu "Presets" nach dem alten Prinzip komplett aus dem gesamten Projekt und aus der Documentation. Ausnahme davon sind alle Dateien, die sich im Ordner "docs\planning" befinden, diese beachte dabei nicht und lass sie unverändert...

- Überprüfe im gesamten Projekt alle vorkommen von "Presets", ob sie sich auf das neue Prinzip beziehen das in der Datei "08__12_konzept_effekt_dateien.md" beschrieben wird, oder noch auf das alte Prinzip das in "docs\presets.md" erklärt wird...
- Entferne alles zu "Presets" nach dem alten Prinzip komplett aus dem gesamten Projekt und aus der Documentation. 



### Zum 
- Die Logik des eigentlichen led_controller-Service soll lediglich mit den fertigen `.lefx` und `.lefxset` umgehen können,d.h. sie lesen um die die effekte, presets und commands zu registrieren und korrekt wiedergeben können.

- Überprüfe im Ordner "src/engine" die Dateien "effect_preset_registry.py", "effect_package_schema.py", "effect_package_builder.py" oder "effect_command_registry.py" und ggfs weitere Dateien, um die Logik korrekt wie hier beschrieben zuschneiden und implementieren zu können.
- Die bisherige Definition der Effects aus "src\led_effects\effects" soll auf das neue System umgestellt werden.

### Zum Building der `.lefx` und `.lefxset`-Dateien
- Alle Effekte sollen nach dem neuen Prinzip in `.lefx`-Dateien ( so wie in "08__12_konzept_effekt_dateien.md" ab Punkt 3 beschrieben) definiert werden, auch die default/builtin-Effekte. 
- Das Building der `.lefx` und `.lefxset`  komplett unabhängig mit eigenständigen Tools sein soll. Das soll insgesamt nur innerhalb des Ordners "tools\effect_building" stattfinden.
- Der `.lefx`-build-flow soll die fertigen `.lefx`-Dateien in "tools\effect_building\build_lefx\<source_id>" speichern.
- Der `.lefxset`-build-flow soll aus diesen <source_id>-Ordnern die enthaltenen `.lefx`-Dateien in eine `.lefxset`-Datei zusammenpacken und unter in "tools\effect_building\build_lefxset\<source_id>.lefxset" speichern. Dafür soll es ein eigenes Script geben ("tools\effect_building\build_lefxset.py")





## Umstellung auf Effect-Engine

- Das Layer-System 

Und ja, alle anderen Wege sollen halt vorher irgendwie gekapselt werden oder in der Engine irgendwie integriert werden, dass die Engine quasi als Hauptverantwortung hat, die LED-Effekte auszugeben und alles strukturell eben davor angesiedelt ist. 

### Umstrukturierung / Neuausrichtung des led_controller

-Ich möchte mit dir hier eine Umstrukturierung / Neuausrichtung vornehmen, bei der das Prinzip eher als ein dauerhaft laufender Dienst ausgerichtet soll, statt nur für die Ausgabe einzelner konkreter Effekte...
- Bitte verschaffe dir einen Überblick über dieses Projekt..Lese dazu die Docs (insbesondere auch den Dev-Teil) und analysiere den Code... Das Ziel dabei ist es dass du das Projekt insgesamt verstehst und auch den genauen aktuellen Stand. Erst danach lese bitte den Rest meiner Nachricht ab hier.
Bitte 
- Erstelle eine md-Datei in der du eine ausführlichen Bericht zu dem geplanten Änderungen verfasst. Ich möchte daran erkennen können ob du denn Sinn und Zweck, sowie alles wesentlichen Informationen auf dem Schirm hast...  
- Anschliessend ergänze dort einen Abschnitt mit deiner Einschätzung, wichtigen Ergänzungen und weiteren Vorschlägen, sowie möglichen Stolperfallen und Problemen die wir beachten sollten...

	

### Engine 
- Die Effekte sollen alle nur über die vorhandene Engine ausgegeben werden, die sie in das Layer-System "einsortiert".
- Es soll keine Wege mehr an der Engine vorbei geben: Alle Eingabe-Formen (CLI, API, Adapter, Wrapper, ...) müssen vorher durch Preprocessing/Normalisierung vereinheitlicht werden...("übersetzt in die Sprache, die die Engine versteht")
- Zum Schluss mache einen Vorschlag, wie wir das Ganze angehen....

### Effekte
- Vereinheitlichung: Alle Effekte sollen durch ein einheitliches Grundschema definiert werden können, das von der Engine verarbeitet wird:
  - Das Grundschema könnte eine Kombination sein aus 
    - Python-Methode (für die Logik)
    - Nicht-Änderbare Eigenschaften (z.B. eindeutige id in snake_case, Layer-Einschränkungen,...) 
      -> Damit es überhaupt funktionieren kann, alle Effekte in einem einheitlichen Schema zu definieren, müssen die unterschiedlichen Anforderungen über feste, nicht änderbare Eigenschaften geregelt werden.
	  -> Beispiel: Auf den unteren beiden "State-" Layern werden Effekte für eine unbestimmte Dauer gesetzt, die solange laufen bis es geändert wird. Es muss also sichergestllt werden, dass nur Effekte die die Voraussetzungen erfüllen (entweder rein statisch oder Dauer-Loop-fähig) dort gesetzt werden können. Im Gegensatz dazu ist für die Effekte auf den anderen Layern ein einmaliges Abspielen vorgesehen.
	  -> Mögliche Lösung: In den Eigenschaften eines Effekts wird festgelegt, für welche Layer er unter welchen Bedingungen freigegeben ist...z.B. kann für die State-Layer die Voraussetzung duration=0 sein, da eine feste Dauer dort nicht passt... Mit festgelegter Dauer kann der selbe Effekt dann jedoch für die anderen Layer geeignet sein... 
    - Änderbare Eigenschaften (z.B. Farbe, Geschwindikeit, Dauer,...)
	  -> Variable Eigenschaften, mit denen die Darstellung der Effekte beeinflusst/konfiguriert werden kann.
	  -> Die Angabe der variablen Eigenschaften soll IMMER nur optional sein, deswegen MUSS für jede ein Default-Wert in denNicht-Änderbaren Eigenschaften hinterlegt sein..
      -> z.B. Farbe, Geschwindikeit, Dauer, transparenz(Bool der festlegt, ob bei ungenutzten LED's der Effekt des Layers darunter durchscheinen darf)...


### Layer
- Die Engine selbst soll Bedeutungsneutral sein, deshalb muss u.A. die bisherige Benennung der Layer geändert werden. (Auflistung der Layer mit Beschreibung/Priorität erkläre Ich weiter unten)
- Das Layer-System stellt immer die aktuelle Ausgabe dar und regelt die Priorisierung/ Überlagerung von Effekten.
- Der Composer baut erstellt aus den Layern von unten nach oben die aktuelle Scene, die vom Renderer gerendert wird. (Prinzip in 'docs\dev\runtime_layers.md' beschrieben) 
- In jedem Layer kann zur selben Zeit immer nur 1 Effekt gesetzt sein. Setzten einen neuen Effekts überschreibt vorherigen. Anzeige kann mit enabled-Bool temporär (de-) aktiviert werden, der gesetzte Effekt bleibt dabei erhalten.


#### BACKGROUND_STATE_LAYER
- BACKGROUND_STATE_LAYER_PRIORITY = 100
- Dieser Layer stellt die unterste Ebene und damit den Idle-State dar. Dieser Layer ist primär für den "Ruhe- bzw. Standby-Zustand" gedacht, solange keine Anwendung etwas gesetzt hat...
- Besonderheit: Der hier gesetzte Zustand wird immer persistent in einer Datei gespeichert, die bei allen Änderungen aktualisiert wird und bei start/neustart wird die Datei gelesen um den eingestellten Effekt wieder setzten zu können. (Fallback: Falls keine Datei gefunden wird -> alle LED's off... Sobald dann etwas geändert/gesetzt wird->Datei wird erstellt)   
- Beispiel: mit geringer Helligkeit, statisch oder leicht pulsierend

#### STATE_LAYER
- STATE_LAYER_PRIORITY = 200
- Dieser Layer ist dazu gedacht,dass die Anwendungen die den Service nutzen einen Zustand darstellen. 
	
#### MAIN_LAYER
- MAIN_LAYER_PRIORITY = 300
- Haupt-Effekt... Hier habe ich an keinen speziellen UseCase gedacht... Anwendungen können sich hier kreativ austoben..

#### TEMP_OVERLAY_LAYER
- TEMP_OVERLAY_LAYER_PRIORITY = 400
- Layer für Zeitlich begrenzte Effekte, die temporär als Overlay über den Haupteffekt/State gelegt werden sollen
- Beispiele dafür könnten sein z.B. Timer- oder Fortschrittsanzeigen sein, die bis zu ihrem Abschluss übergelegt werden..

#### ONGOING_OVERLAY_LAYER
- ONGOING_OVERLAY_LAYER_PRIORITY = 500
- Layer für Zeitlich unbegrenzte Effekte, die temporär als Overlay über die unteren Layer gelegt werden.
- Beispiele dafür könnten sein z.B. Eine DoA-Anzeige, die bei erkannten Geräuschen mit einer LED die Richtung anzeigt... Sie könnte mit transparent=true so konfiguriert werden, dass sie bis auf die eine LED die restliche Anzeige nicht beeinträchtigt.
	
#### EVENT_LAYER
- EVENT_LAYER_PRIORITY = 600
- Kurze Effekte mit höchster Priorität...Könnte kurzes aufblitzen oder rotieren sein.
- Falls mehrere in kurzer Zeit gesetzt werden, werden diese in einer Warteschlange nacheinander angezeigt.
- Gedacht zum signalisieren kurzer Benachrichtigungen, wie Fehler, Warnungen,etc...













