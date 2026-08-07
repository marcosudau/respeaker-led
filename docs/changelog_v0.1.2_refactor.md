# Dokumentation aller Änderungen seit dem 06.08.2026

Dieses Dokument beschreibt umfassend alle technischen Änderungen, Refactorings, CI/CD-Optimierungen und Veröffentlichungen, die seit Beginn der Arbeiten am **06.08.2026** in den beiden GitHub-Repositories durchgeführt wurden:

1. **Haupt- & Entwicklungs-Repository**: [`marcosudau/led_controller_respeaker`](https://github.com/marcosudau/led_controller_respeaker)
2. **Release- & PyPI-Repository**: [`marcosudau/respeaker-led`](https://github.com/marcosudau/respeaker-led)

---

## 1. Übersicht & Meilensteine

- **Erste PyPI-Veröffentlichung (`respeaker-led==0.1.2`)**: Das Paket wurde offiziell auf [PyPI (respeaker-led)](https://pypi.org/project/respeaker-led/) publiziert.
- **Passwortloses PyPI-Publishing (OIDC Trusted Publisher)**: Einrichtung von GitHub Actions mit OIDC-Token zur automatisierten und sicheren Veröffentlichung ohne API-Tokens.
- **Ordnerstruktur & Import-Refactoring**: Umstellung des Quellcodes auf die Python-Standardstruktur `src/respeaker_led/`, sodass Nutzer nach `pip install respeaker-led` direkt `from respeaker_led import ControllerService` ausführen können.
- **Dual-Repository-Strategie**:
  - `respeaker-led`: Schlankes, sauberes Release-Repository für das PyPI-Paket.
  - `led_controller_respeaker`: Vollständiges Entwicklungs-Repository mit PySide6-Demo-App, Entwickler-Tools, Testsuiten und PyInstaller-Build-Pipeline.
- **PySide6 & Demodateien ausgelagert**: Die über 100 MB schwere PySide6-Abhängigkeit wurde aus den Kern-Abhängigkeiten entfernt und als optionales Extra (`pip install respeaker-led[demo]`) bereitgestellt.

---

## 2. Chronologische Commit-Historie (ab 06.08.2026)

| Commit Hash | Datum & Uhrzeit | Commit Message | Beschreibung / Ziel |
| :--- | :--- | :--- | :--- |
| `c048fbf` | 2026-08-06 23:38:18 | `feat: prepare clean respeaker-led PyPI release package with USB daemon resilience and embedded ControllerService integration` | Vorbereitung des initialen sauberen Release-Standes für PyPI. |
| `4e05da0` | 2026-08-06 23:49:57 | `docs: add dynamic effect set loading guide` | Dokumentation zu Option 3 (dynamisches Nachladen von `.lefx` / `.lefxset` Effektpaketen zur Laufzeit via CLI und Python API). |
| `e276831` | 2026-08-06 23:59:38 | `ci: add GitHub Actions workflow for automated OIDC PyPI publishing` | Erstellung von `.github/workflows/release.yml` für PyPI Trusted Publishing via OIDC. |
| `8943f0f` | 2026-08-07 00:04:19 | `docs: add release and update guide for GitHub and PyPI` | Erstellung von `docs/release_guide.md` als Anleitung für künftige Releases (mit und ohne PyPI). |
| `9e10ab6` | 2026-08-07 00:07:10 | `chore: bump version to 0.1.2 for first official release` | Anheben der Paketversion in `pyproject.toml` und `build-tools/version.py` auf `0.1.2`. |
| `eb28526` | 2026-08-07 00:14:44 | `ci: add release event trigger` | Ergänzung des `release`-Triggers in der GitHub Action `release.yml`. |
| `e43a7f8` | 2026-08-07 00:42:01 | `feat: include PySide6 demo app and full dev suite for v0.1.2` | Einpflegen aller Entwicklertools und der PySide6-Demo in das Hauptrepository `led_controller_respeaker`. |
| `a80c34a` | 2026-08-07 01:04:48 | `refactor: finalize standard src/respeaker_led package structure for v0.1.2` | **Haupt-Refactoring**: Quellcode nach `src/respeaker_led/` verschoben, `pyproject.toml` angepasst, 192/192 Tests aktualisiert und Abwärtskompatibilität gesichert. |
| `d48d076` | 2026-08-07 01:05:02 | `chore: exclude examples from release repo` | Ausschluss des `examples/`-Ordners in `.gitignore` für das saubere PyPI-Release-Repo `respeaker-led`. |
| `7749e30` | 2026-08-07 01:11:20 | `ci: publish to PyPI only from release repo marcosudau/respeaker-led` | Hinzufügen der Bedingung `if: github.repository == 'marcosudau/respeaker-led'` im Release-Workflow, um PyPI Auth-Fehler im Entwicklungs-Repo zu vermeiden. |
| `85bbfe1` | 2026-08-07 01:17:24 | `ci: sync --all-extras to install PySide6 in CI workflow` | Ergänzung von `--all-extras` in `.github/workflows/ci.yml`, um PySide6 für Tests in GitHub Actions bereitzustellen. |
| `0d36417` | 2026-08-07 01:18:35 | `ci: add workflow_dispatch to ci.yml` | Ergänzung von `workflow_dispatch` in `ci.yml` zur manuellen Ausführung über die GitHub UI oder die `gh` CLI. |
| `82d4f3f` | 2026-08-07 01:20:07 | `ci: add contents: read permission to release.yml` | Erweitern der Workflow-Permissions um `contents: read`, damit `actions/checkout` Zugriff auf private Repositories hat. |
| `8365336` | 2026-08-07 01:21:46 | `ci: add fetch-depth: 0 and repository to checkout in release.yml` | Hinzufügen von `fetch-depth: 0` und expliziter Repository-Angabe im `release.yml` Checkout-Schritt für stabile Tag-Checkouts. |

---

## 3. Detaillierte Beschreibung aller Änderungen

### 3.1. Standardisiertes Paket-Layout (`src/respeaker_led/`)

#### Problem
Zuvor lag der Code direkt unter `src/*.py`. Hatchling war in `pyproject.toml` wie folgt konfiguriert:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src"]
```
Dadurch wurde beim Installieren via Pip der Quellcode als Modul `src` in `site-packages/src` abgelegt. Ein Import mit `from respeaker_led import ControllerService` schlug fehl mit `ModuleNotFoundError: No module named 'respeaker_led'`.

#### Lösung & Umsetzung
1. **Dateiverschiebung**: Alle Quelldateien aus `src/` wurden in das neue Unterverzeichnis `src/respeaker_led/` verschoben.
2. **Build-Konfiguration (`pyproject.toml`)**:
   ```toml
   [tool.hatch.build.targets.wheel]
   packages = ["src/respeaker_led"]

   [project.scripts]
   respeaker-led = "respeaker_led.interfaces.cli:main"
   ```
3. **Pfade in `paths.py` angepasst**:
   ```python
   PACKAGE_ROOT = Path(__file__).resolve().parents[1]  # src/respeaker_led
   RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", PACKAGE_ROOT.parents[1])).resolve()
   SOURCE_ROOT = PROJECT_ROOT / "src" / "respeaker_led"
   ```
4. **Abwärtskompatibilität für Effekte**:
   In `src/respeaker_led/engine/effect_package_builder.py` wurden `sys.modules`-Aliase hinterlegt:
   ```python
   sys.modules.setdefault("src", respeaker_led)
   sys.modules.setdefault("src.core", respeaker_led.core)
   sys.modules.setdefault("src.core.effect_schema", respeaker_led.core.effect_schema)
   sys.modules.setdefault("src.core.color_math", respeaker_led.core.color_math)
   ```
   Dadurch können auch bestehende oder benutzerdefinierte Effekte, die `from src.core...` importieren, weiterhin ohne Fehler geladen werden.
5. **Testsuite-Aktualisierung**: Alle 192 Unit- und Integrationstests wurden von `from src...` auf `from respeaker_led...` umgestellt.

---

### 3.2. PyPI Release-Optimierung & PySide6 Extra Target

- **Schlankes Kernpaket**: Die Schwergewicht-Abhängigkeit `PySide6` (>100 MB) wurde aus den Hauptabhängigkeiten entfernt.
- **Optionales Extra `demo`**:
  ```toml
  [project.optional-dependencies]
  demo = ["pyside6>=6.5.0"]
  ```
  Nutzer können das Paket schlank installieren (`pip install respeaker-led`) oder mit GUI-Demo (`pip install respeaker-led[demo]`).
- **Demo-App**: Die PySide6 GUI wurde in `examples/pyside6_demo.py` isoliert und ist im Hauptrepository `led_controller_respeaker` enthalten.

---

### 3.3. Dynamisches Nachladen von Effekten (Option 3)

In `docs/integration_guide.md` wurde die Nutzung von dynamischen Effektpaketen dokumentiert. Das System unterstützt das Registrieren von externen `.lefx` und `.lefxset` Dateien zur Laufzeit:
- **CLI**:
  ```bash
  respeaker-led register-effect-source /path/to/custom-effects.lefxset
  ```
- **Python API**:
  ```python
  from respeaker_led import ControllerService

  with ControllerService() as service:
      service.runtime.effect_registry.register_effect_source("/path/to/custom-effects.lefxset")
  ```

---

### 3.4. PyPI OIDC Trusted Publishing & GitHub Actions CI/CD Fixes

#### PyPI Trusted Publisher (OIDC)
Im PyPI-Account von `marcosudau` wurde ein Trusted Publisher für das Repository `marcosudau/respeaker-led` mit dem Workflow `release.yml` konfiguriert. Dadurch sind keine API-Tokens oder Passwörter in den GitHub Secrets erforderlich.

#### Release-Workflow (`.github/workflows/release.yml`)
- Trigger auf Tags `v*.*.*` sowie manuellen `workflow_dispatch`.
- Hinzugefügt: `permissions: contents: read`, `id-token: write`.
- Hinzugefügt: `fetch-depth: 0` und `repository: ${{ github.repository }}` im Checkout-Schritt.
- Hinzugefügt: Repository-Filter `if: github.repository == 'marcosudau/respeaker-led'`, um im Hauptrepository den Publish-Schritt sauber zu überspringen.

#### CI-Workflow (`.github/workflows/ci.yml`)
- Hinzugefügt: `uv sync --all-groups --all-extras`, um PySide6 für GUI-Tests im CI-Environment bereitzustellen.
- Hinzugefügt: `workflow_dispatch` Trigger zur manuellen Ausführung über die GitHub CLI/UI.

---

## 4. Vergleich der Repositories

| Eigenschaft | Release Repo (`marcosudau/respeaker-led`) | Dev Repo (`marcosudau/led_controller_respeaker`) |
| :--- | :--- | :--- |
| **Hauptzweck** | PyPI Paket-Distribution & Clean Source | Volle Entwicklungssuite, Demos, Build-Pipelines |
| **PyPI Publishing** | Ja (OIDC Trusted Publisher aktiv) | Übersprungen (Baut & testet nur) |
| **Entwicklungs-Tools** | Basis-Paket & Core CLI | PySide6 App, PyInstaller, Build Scripts, Tutorials |
| **`examples/` Ordner** | In `.gitignore` ausgeschlossen | Vollständig enthalten (`examples/pyside6_demo.py`) |
| **Aktueller Tag** | `v0.1.2` | `v0.1.2` |

---

## 5. Verifikations- & Testergebnisse

- **Pytest Test-Suite**: `192 passed` in 166s.
- **PyPI Status**: Version `0.1.2` ist live und installierbar unter `https://pypi.org/project/respeaker-led/`.
- **Import-Test in frischer venv**:
  ```powershell
  pip install --upgrade respeaker-led
  python -c "from respeaker_led import ControllerService; print('OK')"
  ```
  Output: `OK`
- **GitHub Actions Status**:
  - `marcosudau/respeaker-led`: **Success (Grün)**
  - `marcosudau/led_controller_respeaker`: **Success (Grün)** (Runs: `31130788728`, `31130964017`).
