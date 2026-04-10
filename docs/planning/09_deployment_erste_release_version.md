# Deployment- Und Release-Konzept Fuer Den LED-Controller

Stand: 2026-04-10
Status: Planungsdokument, keine Implementierung in diesem Konzeptteil

## Zielbild

Fuer den LED-Controller gibt es zwei sinnvolle Betriebsarten, aber nicht beide haben denselben Reifegrad und dieselben Anforderungen.

Die erste Release-Version sollte bewusst auf den pragmatischeren Weg zielen:

- der LED-Controller wird von einer Host-Anwendung als Unterprozess gestartet
- die Host-Anwendung steuert den laufenden Service lokal per CLI oder HTTP
- Packaging und Distribution bleiben so einfach wie moeglich

Der mittel- bis langfristige Zielzustand kann danach folgen:

- der LED-Controller wird als eigenstaendiger Windows-Dienst installiert
- er startet automatisch mit dem System
- er ist in den Windows-Diensten sichtbar
- Restart- und Betriebsverhalten folgen dem ueblichen Windows-Service-Modell

## Einordnung der zwei Nutzungsarten

### 1. Kurzfristig: Unterprozess der Host-Anwendung

Das ist fuer eine erste Release-Version klar der richtige Weg.

Vorteile:

- deutlich weniger Infrastrukturaufwand
- keine Service-Installation und keine Windows-spezifische Dienstverwaltung noetig
- einfacheres Debugging
- schnellere Iteration in Entwicklung und fruehen Releases
- saubere Prozesshoheit durch die Host-Anwendung

Nachteile:

- Lebensdauer des LED-Controllers ist an die Host-Anwendung gekoppelt
- kein nativer Eintrag in Windows-Dienste
- Restart und Fehlerbehandlung muessen vorerst von der Host-Anwendung uebernommen werden

Einschaetzung:

Fuer eine erste Release-Version ist das der effektivste und risikoaermste Weg.

### 2. Mittel- bis langfristig: Eigenstaendiger Windows-Dienst

Das ist architektonisch ein gutes Zielbild, aber nicht der erste sinnvolle Release-Schritt.

Vorteile:

- systemweiter, stabiler Dienst
- entkoppelt von der Host-Anwendung
- automatischer Start und Restart moeglich
- klarer Betriebszustand ueber Windows-Dienstverwaltung

Nachteile:

- deutlich mehr Installations- und Betriebslogik
- Windows-Service-Wrapper oder nativer Dienstmodus notwendig
- sauberer Umgang mit Logs, Pfaden, Berechtigungen und Updates wird wichtiger
- Fehlerbilder werden betrieblicher und weniger entwicklungsnah

Einschaetzung:

Das ist ein gutes Ziel fuer spaetere Releases, aber kein guter Kandidat fuer den schnellsten ersten produktiven Build.

## Was fuer die erste Release-Version effektiv noch fehlt

Wenn man das Zielbild "Host-Anwendung startet den LED-Controller als Unterprozess" ernst nimmt, fehlen im Wesentlichen noch diese Dinge:

### A. Ein klar definierter Startvertrag

Die Host-Anwendung braucht eine stabile Art, den Prozess zu starten.

Dazu gehoeren:

- exakter Startbefehl
- host und port
- readiness-Pruefung
- sauberer Shutdown
- definierte Timeout- und Retry-Regeln

Beispielhaft muss die Host-Anwendung festlegen:

- wann der Prozess gestartet wird
- wie lange auf `ping` oder `health` gewartet wird
- was passiert, wenn der Start fehlschlaegt
- wann `shutdown` gesendet wird

### B. Ein Release-taugliches Startpaket

Fuer den ersten Release reicht kein lose verteiltes Quellrepo.

Du brauchst ein klar benennbares Auslieferungsartefakt mit:

- dem eigentlichen Launcher
- der Python-Laufzeit oder einer eingebetteten Laufzeitstrategie
- der Service-Implementierung
- den Effektmodulen
- optionalen Presets
- Konfigurationsdateien

### C. Ein kleines Konfigurationsmodell

Spaetestens fuer Release sollte nicht alles implizit im Code oder im Startkommando stecken.

Mindestens sinnvoll sind:

- Host
- Port
- FPS
- Device-Modus oder Preview-Modus
- Log-Level
- Pfad fuer persistierte Runtime-Daten

### D. Ein reproduzierbarer Build-Prozess

Es muss klar sein:

- wie aus dem Repo ein Release-Build entsteht
- welche Python-Version verwendet wird
- wie Abhaengigkeiten eingefroren werden
- wie das Ergebnis verpackt wird

### E. Ein Betriebsmodell fuer Fehlerfaelle

Auch in der ersten Release-Version braucht ihr ein Minimum an Betriebssicherheit.

Dazu gehoeren:

- Startfehler erkennen
- Prozessabsturz erkennen
- kontrolliertes Neu-Starten ueber die Host-Anwendung
- Logging fuer Diagnose

## Meine Empfehlung fuer die erste Release-Version

Ich wuerde die erste Release-Version als "lokal gebundener Service-Prozess" ausliefern.

Das bedeutet:

- der Controller bleibt ein eigener Prozess
- die Host-Anwendung startet und beendet ihn
- die Kommunikation bleibt lokal ueber HTTP
- Packaging liefert einen direkt startbaren Windows-Build mit

Das ist ein guter Mittelweg zwischen sauberer Entkopplung und geringem Betriebsaufwand.

## Empfohlenes Distributionsformat fuer Release 1

Fuer Windows gibt es zwei realistische Wege.

### Variante A: Python ist Teil des Release-Artefakts

Auslieferung zum Beispiel als ZIP oder Installer mit:

- `led-controller.exe` oder `start-controller.cmd`
- eingebetteter Python-Runtime oder gebuendeltem Interpreter
- Anwendungscode
- `src/led_effects/effects/`
- `src/led_effects/preset_packs/`
- Konfigurationsdatei

Vorteile:

- voller Python-Stack bleibt sichtbar und wartbar
- Debugging einfacher
- interne Updates an Skripten leichter

Nachteile:

- mehr Dateien im Release
- Python-Runtime muss sauber mitgeliefert werden

### Variante B: Gepacktes Windows-Executable-Bundle

Zum Beispiel per PyInstaller, Nuitka oder aehnlichem Tool.

Auslieferung zum Beispiel als:

- einzelnes EXE-Binary oder
- Ordner mit EXE plus Datenverzeichnissen

Vorteile:

- einfachere Auslieferung
- fuer Endnutzer weniger Python-sichtbar
- geringere Einstiegshuerde beim Start

Nachteile:

- Packaging-Komplexitaet steigt
- Debugging und Fehleranalyse werden etwas haerter
- Datenordner wie `src/led_effects/effects/` und Presets muessen im Build explizit mitgenommen werden

## Meine konkrete Empfehlung zum Format

Fuer die erste produktive Windows-Version:

1. Build eines dedizierten Startartefakts fuer den Controller.
2. Auslieferung als Ordnerstruktur oder ZIP mit klarer Startdatei.
3. Noch keinen nativen Windows-Dienst daraus machen.
4. Falls moeglich ein einzelnes EXE als Launcher, aber die Effekt- und Preset-Daten weiterhin als normale Ordner daneben lassen.

Warum:

- Effektmodule und Presets bleiben so leichter austauschbar.
- Die Host-Anwendung kann den Pfad stabil referenzieren.
- Fehleranalyse bleibt realistischer als bei einem zu frueh stark verdichteten Binary.

## Vorschlag fuer die Release-Ordnerstruktur

Ein sinnvolles erstes Release-Artefakt koennte so aussehen:

```text
led-controller-release/
  controller/
    led-controller.exe
    controller.config.json
    src/
      led_effects/
        effects/
        preset_packs/
    runtime_state/
      background_state.json
    logs/
  docs/
    quickstart.md
    troubleshooting.md
```

Alternativ, wenn Python sichtbar bleibt:

```text
led-controller-release/
  python/
  app/
    main.py
    src/
      led_effects/
      python_control/
  controller.config.json
  start-controller.cmd
```

## Moeglicher Build-Prozess fuer Release 1

## Build-Schritt 1: Python-Version und Abhaengigkeiten fixieren

Vor jedem Release muss klar sein:

- welche Python-Version verwendet wird
- welche Bibliotheken exakt enthalten sind
- ob Abhaengigkeiten reproduzierbar installierbar sind

Konkretes Ergebnis:

- definierte Ziel-Python-Version
- eingefrorene Abhaengigkeitsliste

## Build-Schritt 2: Test- und Smoke-Gate vor dem Paketieren

Vor einem Release sollten mindestens laufen:

- Vollsuite
- einfacher Starttest des Service
- `ping`
- `list-effects`
- ein `apply-effect`-Smoke-Test
- Shutdown-Test

## Build-Schritt 3: Release-Bundle erzeugen

Abhaengig vom gewaehlten Format:

- EXE oder Launcher bauen
- `src/led_effects/effects/` einpacken
- `src/led_effects/preset_packs/` einpacken
- Konfiguration und Standardverzeichnisse anlegen

## Build-Schritt 4: Release-Struktur pruefen

Wichtige Punkte:

- startet das Artefakt auf einem sauberen Windows-System?
- funktioniert der Service ohne Entwickler-Umgebung?
- funktionieren Effekt-Discovery und Preset-Discovery noch?
- ist der Persistenzpfad schreibbar?

## Build-Schritt 5: Host-Anwendungsintegration pruefen

Die Host-Anwendung muss den finalen Build wirklich so starten, wie er spaeter ausgeliefert wird.

Nicht nur lokal aus dem Repo testen, sondern mit dem echten Release-Artefakt.

## Ein moeglicher Startvertrag zwischen Host-App und Controller

Die Host-Anwendung sollte den Controller-Prozess nicht "irgendwie" starten, sondern nach einem klaren Vertrag.

### Start

- Prozess starten
- auf `GET /api/v1/ping` warten
- bei Timeout gezielt abbrechen und neu versuchen

### Betrieb

- periodisches Ping oder Status-Check optional
- Fehler der API klar loggen

### Beenden

- zuerst `shutdown` senden
- wenn noetig nach Timeout Prozess hart beenden

### Restart

- wenn Prozess abstuerzt, darf die Host-Anwendung ihn neu starten
- maximale Retry-Regeln definieren

## Was fuer die erste Release-Version jetzt konkret noch zu tun waere

Hier ist die aus meiner Sicht praktische Reihenfolge.

### 1. Release-Ziel fuer Version 1 explizit festlegen

Beschluss:

- Unterprozess-Modell ist offizieller Release-1-Weg
- Windows-Dienst ist Folgephase

Ohne diese Festlegung verzettelt ihr euch zwischen zwei Betriebsmodellen.

### 2. Start- und Shutdown-Vertrag definieren

Es braucht eine kurze, verbindliche Spezifikation fuer:

- Startkommando
- Readiness
- Shutdown
- Fehlercodes
- Port- und Timeout-Verhalten

### 3. Release-Konfiguration einfuehren

Es braucht eine kleine Konfigurationsdatei oder einen stabilen Konfigurationsmechanismus fuer:

- Port
- FPS
- Device-Nutzung
- Log-Level
- Persistenzpfade

### 4. Build-Werkzeug festlegen

Entscheidung zwischen zum Beispiel:

- Python sichtbar mit eingebettetem Interpreter
- PyInstaller- oder Nuitka-basierter Build

Hier sollte frueh entschieden werden, damit spaetere Deployments nicht doppelt gebaut werden.

### 5. Release-Artefakt standardisieren

Es muss genau ein offizielles Release-Format geben, nicht mehrere halb fertige Varianten.

### 6. Host-App-Ende-zu-Ende-Test mit echtem Artefakt bauen

Die Host-Anwendung muss gegen den gepackten Controller getestet werden, nicht nur gegen das Entwicklersetup.

### 7. Logging und Fehlerdiagnose release-tauglich machen

Mindestens noetig:

- Logdatei oder klarer Konsolenkanal
- Startfehler sichtbar
- Adapterfehler sichtbar
- API-Fehler sichtbar

### 8. Release-Checkliste einfuehren

Vor jeder Auslieferung sollte eine feste Liste abgearbeitet werden.

Zum Beispiel:

- Tests gruen
- Smoke-Test gruen
- Start aus Release-Artefakt erfolgreich
- Device-Pfad oder Preview-Pfad erfolgreich
- Persistenzpfad schreibbar
- Effekt-Discovery intakt

## Worauf ihr zusaetzlich achten solltet

## 1. Pfade und Schreibrechte

Das wird spaetestens bei Windows-Diensten wichtig, aber schon in Release 1 sollte klar sein:

- wo Logs liegen
- wo Persistenzdateien liegen
- welche Verzeichnisse beschreibbar sein muessen

Gerade ein spaeterer Windows-Dienst sollte keine beschreibbaren Zustandsdateien im Installationsverzeichnis erwarten.

## 2. Portkonflikte

Wenn die Host-Anwendung den Controller als Unterprozess startet, muss klar sein:

- wie ein freier Port gewaehlt wird
- ob der Port fix oder konfigurierbar ist
- was bei bereits laufender Instanz passiert

## 3. Prozessdoppelstarts

Die Host-Anwendung darf den Controller nicht versehentlich mehrfach starten.

Dafuer braucht ihr mindestens:

- Port-Pruefung oder
- PID-/Lockfile-Strategie oder
- explizite Einzelinstanz-Regel

## 4. Update-Strategie

Auch frueh sollte klar sein:

- wie neue Builds ausgeliefert werden
- wie Effektdateien und Presets aktualisiert werden
- ob die Host-Anwendung den Controller mit updated oder getrennt davon

## 5. Hardware-Fehlerbilder

Die erste Release-Version muss klar definieren, was passiert wenn:

- das ReSpeaker-Geraet fehlt
- Initialisierung fehlschlaegt
- der Device-Pfad spaeter ausfaellt

Die wichtigste Frage ist hier:

- bleibt der Controller mit Preview-/Fallback-Modus erreichbar oder gilt das als harter Fehler?

## 6. Trennung von Dev- und Release-Betrieb

Der Release-Build sollte moeglichst nicht mehr denselben lose offenen Charakter wie das Repo haben.

Wichtig ist eine Trennung zwischen:

- Entwicklerstart aus dem Repo
- offizieller Start aus dem Release-Artefakt

## Wie ich den Windows-Dienst spaeter angehen wuerde

Nicht sofort, sondern als bewusste zweite Ausbaustufe.

### Sinnvolle spaetere Schritte

1. stabiler Release-1-Unterprozessbetrieb
2. formalisierte Konfiguration und Logs
3. eigenstaendiger Launcher mit sauberem Exit-Code-Verhalten
4. Dienstwrapper oder nativer Service-Einstieg
5. Installer, Dienstregistrierung und Restart-Policies

### Was ein spaeterer Windows-Dienst zusaetzlich braucht

- Installationsroutine
- Service-Registrierung
- Windows-konforme Start- und Stop-Semantik
- Restart-Policy
- Event-Log- oder Dateilog-Strategie
- sauberer Umgang mit Benutzerrechten und Pfaden

## Zusammenfassung der Empfehlung

Fuer die erste Release-Version wuerde ich klar empfehlen:

- den LED-Controller als separaten lokalen Unterprozess ausliefern
- ihn durch die Host-Anwendung starten und ueberwachen lassen
- ein standardisiertes Windows-Release-Artefakt bauen
- den Build reproduzierbar und testbar machen
- den Windows-Dienst bewusst auf die zweite Ausbaustufe verschieben

Das ist der schnellste Weg zu einer belastbaren ersten Release-Version, ohne die Architektur in eine zu fruehe Betriebsform zu zwingen.