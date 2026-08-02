# Experiment-Workflow

## Ziel

Groessere, riskante oder hardwareabhaengige Arbeiten werden nicht direkt im
kanonischen `main` entwickelt. Sie entstehen zuerst in einem isolierten
Versuchsklon unter einem gemeinsamen Experimente-Ordner.

Der Hauptstand bleibt dadurch:

- jederzeit start- und testbar
- frei von halbfertigen Implementierungen
- frei von zusaetzlichen Experiment-Branches
- die einzige Quelle fuer freigegebenen Produktionscode

Dieser Workflow ist besonders fuer folgende Arbeiten vorgesehen:

- Hardware- und Firmwaretests
- Aenderungen am Effekt-, Layer- oder Paketmodell
- groessere Architekturumbauten
- Performance- und FPS-Versuche
- neue Integrationen mit unklaren Geraete- oder API-Eigenschaften

## Verzeichnisstruktur

Der Standardpfad ist:

```text
%USERPROFILE%\source\experiments\
  .venv\
  <experiment-a>\
  <experiment-b>\
```

`LED_CONTROLLER_EXPERIMENTS_ROOT` kann gesetzt werden, wenn ein anderer
gemeinsamer Experimente-Ordner verwendet werden soll.

Jedes Unterprojekt ist ein eigener lokaler Git-Klon des sauberen `main`.
Der Erzeugungsvorgang entfernt den Remote aus dem Versuchsklon. Experimente
sind dadurch nicht als parallele GitHub-Staende gedacht und koennen nicht
versehentlich gepusht werden.

## Gemeinsame Python-Umgebung

Alle Experimente duerfen die gemeinsame Umgebung
`%USERPROFILE%\source\experiments\.venv` verwenden.

Wichtig:

- Die Umgebung enthaelt nur die Abhaengigkeiten aus `uv.lock`.
- Das Projekt selbst wird nicht in die Umgebung installiert.
- Insbesondere gibt es keine Editable-Installation eines anderen Checkouts.
- Python und Pytest muessen aus dem jeweiligen Experimentordner gestartet
  werden, damit dessen lokales `src/` verwendet wird.

Die Umgebung wird eingerichtet oder auf den aktuellen Lock-Stand gebracht mit:

```powershell
.\build-tools\scripts\setup_experiment_environment.ps1
```

Das Skript verwendet:

```text
uv sync --active --locked --all-groups --no-install-project
```

Wenn ein Experiment absichtlich andere Abhaengigkeiten benoetigt, bekommt es
eine eigene `.venv`. Die gemeinsame Umgebung wird nicht manuell fuer ein
einzelnes Experiment veraendert.

## Neues Experiment anlegen

Das Skript muss aus einem sauberen `main`-Checkout aufgerufen werden:

```powershell
.\build-tools\scripts\new_experiment.ps1 -Name doa-firmware
```

Es fuehrt folgende Schritte aus:

1. `main`, sauberer Arbeitsbaum und vorhandenes `uv.lock` werden geprueft.
2. Ein lokaler Single-Branch-Klon wird unter dem Experimente-Ordner angelegt.
3. Der Git-Remote des Versuchsklons wird entfernt.
4. Quellpfad und Ausgangscommit werden nur in dessen lokaler Git-Konfiguration
   hinterlegt.
5. Die gemeinsame Experiment-Venv wird synchronisiert.

Danach:

```powershell
Set-Location "$HOME\source\experiments\doa-firmware"
& ..\.venv\Scripts\python.exe -m pytest -q
```

## Regeln waehrend eines Experiments

- Der kanonische Hauptstand wird nicht parallel angepasst.
- Das Experiment darf einen bewusst unfertigen oder schmutzigen Arbeitsbaum
  haben.
- Fremde oder gescheiterte Versuche werden nicht ungeprueft hineinkopiert.
- Beobachtungen, Testkommandos und Hardwarevoraussetzungen werden im
  Experiment dokumentiert.
- Vor und nach der eigentlichen Aenderung wird der komplette Testbestand
  ausgefuehrt.
- Erzeugte Effekt- und Release-Artefakte werden mit den vorhandenen
  Verifikationswerkzeugen geprueft.

## Freigabekriterien

Ein Experiment ist erst ein Kandidat fuer `main`, wenn alle zutreffenden Punkte
erfuellt sind:

1. Das Zielverhalten ist fachlich entschieden.
2. Gezielte Tests fuer das neue Verhalten bestehen.
3. Der komplette Testbestand besteht.
4. Build- und Paketartefakte lassen sich reproduzierbar erzeugen und
   verifizieren.
5. Hardware- oder UI-Verhalten wurde, falls relevant, praktisch bestaetigt.
6. Bekannte Einschraenkungen und offene Entscheidungen sind dokumentiert.
7. Der Diff enthaelt keine unabhaengigen Versuchsreste.

## Uebernahme nach main

Die Uebernahme ist eine eigene, kontrollierte Aktion:

1. `main` muss sauber und aktuell sein.
2. Nur die freigegebenen Teile werden auf die aktuelle Architektur uebertragen.
3. Es wird nicht automatisch der komplette Experimentstand gemergt.
4. Nach der Uebernahme laufen erneut gezielte Tests, Gesamttests, Builds und
   gegebenenfalls Hardwaretests.
5. Erst der so gepruefte Stand wird als normaler `main`-Commit gesichert.

Das Experiment bleibt bis zur bestaetigten Uebernahme als Referenz erhalten.
Danach kann es archiviert oder geloescht werden.

## Bedeutung fuer DOA und das Effekteschema

Der Firmwaretest hat bestaetigt, dass Firmware `2.0.10` den verarbeiteten
Sprecher-Azimut auch bei eigener Ringsteuerung liefert. Damit ist DOA technisch
implementierbar.

Die DOA-Integration wird trotzdem nicht isoliert in das derzeitige Effektemodell
uebernommen, wenn dessen groessere Ueberarbeitung unmittelbar bevorsteht.
Stattdessen dient DOA als reales Abnahmeszenario fuer:

- dauerhafte, datengetriebene Overlays
- Layer-Eigentuemerschaft und Verdraengungsregeln
- Aktivierung und Deaktivierung von Effektquellen
- dynamische Effektparameter
- Hardware-Polling und Statusausgabe
- Kalibrierung und Stabilisierung von Richtungswerten

So muss die DOA-Funktion nicht zuerst gegen das alte Schema integriert und
anschliessend beim Effektumbau erneut angepasst werden.
