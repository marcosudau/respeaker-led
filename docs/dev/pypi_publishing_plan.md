# Konzept & Implementierungsplan: Python-Paketierung und PyPI-Veröffentlichung mit CLI-Steuerung

Dieses Dokument erklärt schrittweise, wie ein Python-Projekt für den **Python Package Index (PyPI)** vorbereitet, als Paket veröffentlicht und mit **eigenen Terminal-Befehlen (CLI Entry Points)** ausgestattet wird, sodass Nutzer es einfach über `pip install` installieren und im Terminal nutzen können.

---

## 1. Übersicht & Grundlagen: Wie funktioniert ein PyPI-Paket mit CLI?

### Was passiert bei `pip install <dein-paket>`?
1. **Paket-Download**: `pip` lädt das kompiliertes Paket (`.whl` Wheel) oder das Quellcode-Paket (`.tar.gz` sdist) von PyPI herunter.
2. **Installation der Abhängigkeiten**: Alle in `pyproject.toml` definierten `dependencies` (z. B. `pyusb`, `fastapi`, `pyside6`) werden automatisch mitinstalliert.
3. **Erstellen von Konsolen-Befehlen (CLI Entry Points)**: Wenn in `pyproject.toml` unter `[project.scripts]` Befehle definiert sind, erstellt `pip` im Ausführungs-Ordner von Python (unter Windows z.B. `venv\Scripts\led-controller.exe` oder global `Python3xx\Scripts\led-controller.exe`) ausführbare Wrapper-Dateien.

### Wie unterscheidet sich das vom eigenständigen `.exe` Service?
- **Früher (PyInstaller / Eigenständige EXE)**: Eine riesige `.exe`, die alle Python-Laufzeitumgebungen und Bibliotheken gebündelt hat. Musste manuell gestartet oder als Dienst eingerichtet werden.
- **Jetzt (PyPI-Paket & CLI)**:
  - Ein leichtgewichtiges Python-Paket.
  - Kann als Bibliothek importiert werden (`import led_controller_respeaker`).
  - Kann direkt über Terminal-Befehle bedient werden (z.B. `led-controller service start` oder `led-controller set state pulse`).
  - Der Hintergrund-Service kann bei Bedarf durch CLI-Befehle gestartet/gestoppt werden.

---

## 2. Einrichten eigener Terminal-Befehle (CLI Entry Points)

Um eigene Konsolenbefehle wie `led-controller` oder ein Kürzel wie `ledctl` nach der Installation verfügbar zu machen, wird in `pyproject.toml` der Bereich `[project.scripts]` hinzugefügt.

### Konfigurations-Beispiel in `pyproject.toml`:

```toml
[project.scripts]
led-controller = "src.interfaces.cli:main"
ledctl = "src.interfaces.cli:main"
```

### Wie das funktioniert:
- **`led-controller`**: Der Befehl, den der Nutzer im Terminal / CMD / PowerShell eingibt.
- **`src.interfaces.cli:main`**: Weist Python an, beim Aufruf des Befehls die Funktion `main()` im Modul `src.interfaces.cli` auszuführen.
- Python übergibt automatisch die Argumente aus dem Terminal (`sys.argv`) an diese `main()`-Funktion.

---

## 3. Schritt-für-Schritt Ablauf zur PyPI-Veröffentlichung

### Schritt 1: Vorbereitung & Metadaten in `pyproject.toml`
Bevor ein Paket hochgeladen werden kann, müssen Metadaten geprüft werden:
1. **Paketname**: Der Name auf PyPI muss einzigartig sein. (z. B. `led-controller-respeaker`).
2. **Versionierung**: Z.B. `0.1.0` (Semantische Versionierung: Major.Minor.Patch).
3. **Autoren-Informationen & Lizenz**: Beschreibung, Autor, Lizenz (z.B. MIT).
4. **README-Format**: PyPI rendert die `README.md` direkt auf der Produktseite.

### Schritt 2: Registrierung bei PyPI & TestPyPI
1. **Accounts anlegen**:
   - [PyPI Production Account](https://pypi.org/account/register/)
   - [TestPyPI Account](https://test.pypi.org/account/register/) *(empfohlen für Test-Uploads)*
2. **2-Faktor-Authentifizierung (2FA)** aktivieren: Auf PyPI inzwischen Pflicht.
3. **API Token erstellen**: Unter den Account-Einstellungen ein API Token (oder "Trusted Publisher" via GitHub Actions) einrichten.

### Schritt 3: Erstellen der Paket-Dateien (Build)
Mit Werkzeugen wie `build` oder `hatch` wird der Quellcode in zwei Standard-Formate gepackt:
- **Wheel (`.whl`)**: Das moderne, schnelle Binär/Quell-Format.
- **Source Distribution (`.tar.gz`)**: Das reine Quellcode-Archiv als Fallback.

**Befehl zum Bauen**:
```bash
python -m pip install build
python -m build
```
*(Dies erzeugt die Ordner `dist/` mit den fertigen `.whl` und `.tar.gz` Dateien)*.

### Schritt 4: Lokal testen (vor dem Upload)
Bevor man auf PyPI hochlädt, installiert man das gebaute `.whl` lokal in einer frischen virtuellen Umgebung:
```bash
pip install dist/led_controller_respeaker-0.1.0-py3-none-any.whl
led-controller --help
```

### Schritt 5: Hochladen mit `twine` (oder TestPyPI)
1. **Erst auf TestPyPI hochladen** (um zu prüfen, ob alles stimmt):
   ```bash
   python -m pip install twine
   python -m twine upload --repository testpypi dist/*
   ```
2. **Installation von TestPyPI testen**:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple led-controller-respeaker
   ```
3. **Auf echts PyPI hochladen**:
   ```bash
   python -m twine upload dist/*
   ```

---

## 4. User Review & Entscheidungen

> [!IMPORTANT]
> Bitte prüfe folgende Punkte vor der Umsetzung:

1. **Wunsch-Namen für die CLI-Befehle**:
   - Sollen die Befehle im Terminal `led-controller` und/oder kurz `ledctl` heißen?
2. **Paketname auf PyPI**:
   - Aktuell heißt das Projekt `led-controller-respeaker`. Ist das als PyPI-Name gewünscht?
3. **Architektur-Modus des Services**:
   - Wenn der Nutzer z.B. `led-controller set state pulse` eingibt:
     - **Option A (Client-Server)**: Der CLI-Befehl prüft, ob der Hintergrund-Service bereits läuft und schickt einen HTTP/Socket-Request an ihn. Falls er nicht läuft, kann er ihn optional im Hintergrund starten.
     - **Option B (Direct Hardware access)**: Der CLI-Befehl greift direkt auf das USB-Gerät zu (sofern kein Service den USB-Port blockiert).

---

## 5. Geplante Änderungen am Projekt (Nach Bestätigung)

### 1. `pyproject.toml` anpassen
- Hinzufügen von `[project.scripts]`:
  ```toml
  [project.scripts]
  led-controller = "src.interfaces.cli:main"
  ledctl = "src.interfaces.cli:main"
  ```
- Ergänzen relevanter Metadaten (Keywords, Authors, URLs zu GitHub).

### 2. CLI Entrypoint Verifizierung (`src/interfaces/cli.py`)
- Sicherstellen, dass `main()` sauber Rückgabe-Codes (0 bei Erfolg, != 0 bei Fehler) an das OS liefert.
- Überprüfen, wie Service-Start und Einzelbefehle integriert sind.

### 3. Dokumentation (`README.md`)
- Hinzufügen einer Anleitung für Endanwender:
  - `pip install led-controller-respeaker`
  - Nutzung der CLI-Befehle (`led-controller --help`, `led-controller service start`, etc.).

---

## 6. Verifikationsplan

### Automatische & Manuelle Tests
1. **Build-Test**:
   - Ausführen von `python -m build` (oder `uv build` / `hatch build`) und Überprüfung der erzeugten `.whl`- und `.tar.gz`-Dateien in `dist/`.
2. **Lokale Installationstest**:
   - Installation des erzeugten Wheels in einer temporären Python-Umgebung.
   - Aufrufen von `led-controller --help` und `ledctl --help` im Terminal.
3. **Funktionstest**:
   - Ausführen von Status- und Steuerungsbefehlen über das installierte Paket.
