# Release- & Update-Anleitung für respeaker-led

Diese Anleitung erklärt Schritt für Schritt, wie Änderungen und Updates im Repository `respeaker-led` verwaltet werden — sowohl für einfache Code-Updates (nur auf GitHub) als auch für offizielle Veröffentlichungen (mit automatischem PyPI-Release).

---

## Übersicht: Die zwei Update-Pfade

| Update-Typ | Wann nutzen? | Was passiert? |
|---|---|---|
| **1. Normales Code-Update (Ohne PyPI)** | Bugfixes, interne Doku-Updates, Refactorings | Code wird auf GitHub aktualisiert. **Kein** Paket-Release auf PyPI. |
| **2. Offizielles Release (Mit PyPI)** | Neue Funktionen, wichtige Fixes für Paket-Nutzer | GitHub Actions baut das Paket und veröffentlicht es automatisch auf [PyPI](https://pypi.org/project/respeaker-led/). |

---

## Pfad 1: Normales Code-Update (OHNE PyPI-Release)

Wenn du Änderungen am Code oder der Dokumentation auf GitHub aktualisieren möchtest, ohne eine neue Paket-Version auf PyPI zu veröffentlichen:

### Schritte:

1. **Änderungen durchführen & lokal testen:**
   ```bash
   uv run pytest -q
   ```
2. **Commit erstellen:**
   ```bash
   git add .
   git commit -m "fix: Beschreibung der Änderung"
   ```
3. **Auf GitHub pushen:**
   ```bash
   git push respeaker-led main
   ```

✅ **Ergebnis:** Dein Repository auf GitHub ist aktuell. Auf PyPI bleibt weiterhin die bisherige Version installiert.

---

## Pfad 2: Offizielles Paket-Release (MIT PyPI-Release)

Wenn eine neue Version deines Pakets auf PyPI öffentlich bereitgestellt werden soll, läuft der Prozess vollautomatisch über GitHub Actions und OIDC Trusted Publishing (ohne Passwörter).

```
  1. Version anpassen    2. Commit & Push      3. Git-Tag pushen      4. PyPI-Release
  build-tools/version.py ──► git push ─────────► git push vX.Y.Z ────► GitHub Action
                                                                        baut & lädt hoch
```

### Schritt-für-Schritt-Anleitung:

#### 1. Versionsnummer anpassen
Öffne die Datei [`build-tools/version.py`](../build-tools/version.py) und trage die neue Version ein:
```python
__version__ = "0.1.2"  # z. B. von 0.1.1 auf 0.1.2
```

#### 2. Tests ausführen & Commit erstellen
```bash
# Tests ausführen
uv run pytest -q

# Äußerungen committen
git add .
git commit -m "chore: bump version to 0.1.2"
git push respeaker-led main
```

#### 3. Git-Tag mit der Version erstellen und pushen
Erstelle ein Git-Tag, das **exakt** der Version entspricht (mit vorangestelltem `v`):
```bash
# Tag erstellen
git tag v0.1.2

# Tag auf GitHub pushen
git push respeaker-led v0.1.2
```

#### 4. Automatische Veröffentlichung durch GitHub Actions
Sobald das Tag `v0.1.2` auf GitHub ankommt:
- Startet GitHub automatisch die Workflow-Datei `.github/workflows/release.yml`.
- Das Paket wird mit `uv build` kompiliert.
- Das fertige Wheel & Sdist werden sicher direkt auf PyPI veröffentlicht.
- Unter **`https://pypi.org/project/respeaker-led/`** steht die neue Version sofort zur Verfügung.
- Anwender können das Update direkt mit `pip install --upgrade respeaker-led` installieren.

---

## Zusammenfassung der Befehle für ein PyPI-Release

```bash
# 1. Version in build-tools/version.py anpassen
# 2. Commit & Push
git add .
git commit -m "release: v0.1.2"
git push respeaker-led main

# 3. Tag pushen -> löst PyPI-Release aus!
git tag v0.1.2
git push respeaker-led v0.1.2
```
