# Phase 1: Multi-Set-Buildbericht (PHASE1_MULTI_SET_BUILD_REPORT.md)

Datum: 2026-08-03
Auftrag: LEFX-V2-Buildprozess auf manifestbasierte Multi-Set-Architektur umstellen

---

## 1. Ausgangsproblem

Der First-Party-Build war auf das Set `default-effects` fest verdrahtet:

- `tools/effect_building/standard_effects.py` enthielt eine set-spezifische
  Discovery (`discover_standard_effects`), die ausschließlich
  `sources/<states|overlays|events>/<id>/effect.yaml` verstand und bei jeder
  anderen Struktur hart fehlschlug.
- Die Effektquellen lagen direkt unter `sources/states/`, `sources/overlays/`,
  `sources/events/`.
- Das zweite Set `smartspeaker-set` existierte bereits unter
  `sources/smartspeaker-set/`, wurde aber von der alten Discovery nicht
  verarbeitet; der Build brach ab, sobald die Smartspeaker-Quellen vorhanden
  waren (nachgewiesen durch fehlgeschlagene Test-Kollektion vor der Migration).
- `build_lefx.py` und `build_lefxset.py` kannten nur den einen Sonderweg
  (`build_standard_effect_packages`, `build_standard_effect_set`,
  `DEFAULT_PUBLISH_COPY`).

## 2. Umgesetzte Zielarchitektur

```text
tools/effect_building/sources/*/set.yaml
    -> automatische Set-Discovery
    -> Effektquellen des jeweiligen Sets entdecken und validieren
    -> einzelne .lefx-Pakete bauen und prüfen
    -> aus den vorgebauten .lefx das jeweilige .lefxset bauen
    -> alle fertigen Sets veröffentlichen
```

Ein neues Set wird ausschließlich durch eine gültige
`tools/effect_building/sources/<set-id>/set.yaml` bekannt. Keine
Python-Registry, kein set-spezifischer Import, keine Änderung an einem
Buildskript ist dafür nötig.

## 3. Neu angelegte, geänderte, verschobene und gelöschte Dateien

**Neu angelegt:**
- `tools/effect_building/effect_set_sources.py` (Discovery + Validierung)
- `tools/effect_building/effect_set_builder.py` (Buildorchestrierung)
- `tools/effect_building/sources/default-effects/set.yaml`
- `tools/effect_building/sources/smartspeaker-set/set.yaml`
- `tools/effect_building/PHASE1_MULTI_SET_BUILD_REPORT.md` (diese Datei)

**Verschoben (nur Renames, keine Inhaltsänderung):**
- `tools/effect_building/sources/{states,overlays,events}/`
  → `tools/effect_building/sources/default-effects/{states,overlays,events}/`

**Geändert:**
- `tools/effect_building/__init__.py` (exportiert jetzt die generische API)
- `tools/effect_building/build_lefx.py` (Multi-Set-Paketbuild)
- `tools/effect_building/build_lefxset.py` (Multi-Set-Setbuild, `--publish-copy` entfernt)
- `tools/effect_building/BUILD_PROCESS.md` (Multi-Set-Prozess)
- `build-tools/build_config.json` (`builtin-effects-discovery` auf
  `tools/effect_building/build/output`)
- `tests/conftest.py` (baut alle Sets)
- `tests/test_effect_building.py` (generische Multi-Set-Tests, siehe 7)
- `tests/test_architecture.py` (generische Discovery statt `discover_standard_effects`)
- `tests/test_builtin_effects.py` (Default-Set-Discovery)
- `tests/test_effect_tutorials.py` (Default-Set-Discovery + korrigierter
  Beispielpfad `docs/effect_examples`)
- `.gitignore` (entfernt: `sources/default-effects/` und andere veraltete
  Build-Ignore-Einträge, damit die Set-Manifeste versioniert werden)

**Gelöscht:**
- `tools/effect_building/standard_effects.py` (Sonderweg vollständig entfernt)

**Zusätzlich behobene, vorbestehende Doku-Inkonsistenzen aus dem Commit
„Docs aufgeräumt":**
- `tests/test_documentation_structure.py` (neue Struktur `docs/.archive`,
  `docs/.planning`, reale Archiv-Pfade)
- `tests/test_reset_build_artifacts.py` (neuer Beispiel-Cache-Pfad)
- `docs/effects.md`, `docs/index.md`, `docs/dev/*.md`,
  `docs/effect-development/README.md`, `docs/.planning/index.md` (tote Links)
- `docs/effect-development/tutorials/*.md` (Beispielpfad `docs/effect_examples`)
- `build-tools/scripts/cleanup_paths.json` und `cleanup_after_build.py`
  (Beispiel-Cache-Pfad)

## 4. Set-Manifeste und Source-Struktur

```text
tools/effect_building/sources/
├── default-effects/
│   ├── set.yaml          (set_id/source_id: default-effects)
│   ├── states/   (14 Effektquellen)
│   ├── overlays/ ( 9 Effektquellen)
│   └── events/   (11 Effektquellen)
└── smartspeaker-set/
    ├── set.yaml          (set_id/source_id: smartspeaker-set)
    ├── states/   (10 Effektquellen)
    ├── overlays/ ( 4 Effektquellen)
    ├── events/   ( 9 Effektquellen)
    └── README.md, IMPLEMENTATION_SPEC.md, QUALITY_REPORT.md (unverändert)
```

Die alten direkten Verzeichnisse `sources/states|overlays|events` existieren
nicht mehr. Beide Manifeste enthalten bewusst keine manuelle `effects`-Liste;
alle Quellen unter den typisierten Unterordnern gehören zum Set.

## 5. Discovery- und Validierungsregeln

`discover_effect_sets()`:
1. sucht ausschließlich `sources/*/set.yaml`
2. sortiert deterministisch nach Pfad/`set_id`
3. schlägt klar fehl, wenn kein Set gefunden wird
4. akzeptiert nur die V2-Set-Manifest-Schlüssel
   (`set_id, source_id, title, version, min_service_version, effects,
   description, tags, author, vendor`)
5. erzwingt `set_id` und `source_id`
6. verlangt, dass der Ordnername dem `set_id` entspricht
7. lehnt doppelte `set_id` hart ab
8. lehnt doppelte `source_id` hart ab
9. lehnt verwaiste/legacy Effektquellen außerhalb eines Set-Roots hart ab

`discover_effect_sources(effect_set)`:
- sucht nur in `states/`, `overlays/`, `events/` des konkreten Sets
- `effect.yaml` exakt eine Ebene unter dem Typordner
- `source_id` muss der Set-`source_id` entsprechen
- `package_id == f"{source_id}.{effect_id}"`
- Ordnername == `EffectDefinition.id`
- Typordner entspricht `DefinitionType` (`state->states`, `overlay->overlays`,
  `event->events`)
- `entry_file`/`entry_class` werden generisch aus `effect.yaml` verwendet
- doppelte Effekt-IDs innerhalb eines Sets werden abgelehnt
- gleiche lokale Effekt-IDs in verschiedenen Sets sind zulässig (die
  `source_id` qualifiziert fachlich)

## 6. Buildpfade und CLI-Verhalten

Build-Root aus `LED_CONTROLLER_EFFECT_BUILD_ROOT` (Default:
`tools/effect_building/build`):

```text
<build-root>/.cache/build_lefx/<set-id>/*.lefx
<build-root>/.cache/generated/<set-id>/...
<build-root>/output/<set-id>.lefxset
<build-root>/published/<set-id>.lefxset
```

**`build_lefx.py`** (Multi-Set-Paketbuild, Default ohne Pflichtargumente):
- entdeckt alle `sources/*/set.yaml`
- baut alle Effektpakete aller Sets
- Root-Overrides: `--sources-root`, `--output-root` (gemeinsamer
  Package-Cache-Root, pro Set ein Unterordner)
- JSON-Abschlussbericht mit `set_count`, `effect_count`, `sets`

**`build_lefxset.py`** (Multi-Set-Setbuild):
- Optionen: `--sources-root`, `--packages-root`, `--output-root`,
  `--publish-root`, `--rebuild-packages`, `--keep-cache`
- `--publish-copy` wurde entfernt (passt nicht zu mehreren Sets)
- Set-Build ausschließlich aus vorgebauten `.lefx`; fehlende, zusätzliche oder
  fremde Pakete führen zu hartem Fehler
- Cache-Cleanup erst nach Erfolg aller Sets; `--keep-cache` erhält den Cache

## 7. Testabdeckung

`tests/test_effect_building.py` deckt ab:

- Discovery: beide realen Sets gefunden, deterministische Reihenfolge,
  34/23 Quellen, doppelte `set_id`/`source_id` abgelehnt, Ordnername-Mismatch
  abgelehnt, Legacy-/Orphan-Quelle abgelehnt, kein Set gefunden → Fehler,
  falscher Typordner abgelehnt, falsche `source_id`/`package_id` abgelehnt,
  unbekannte Manifest-Schlüssel abgelehnt
- Paketbuild: beide Sets, getrennte Verzeichnisse, 57 Pakete gesamt,
  jedes Paket ladbar, Smoke-Render erfolgreich
- Set-Build: beide `.lefxset` aus vorgebauten Paketen, ladbar, exakte
  Effektmengen (34/23), keine Source-Ordner-Warnung, fehlendes Paket abgelehnt,
  veraltetes Zusatzpaket abgelehnt, falsche `source_id` abgelehnt,
  `--rebuild-packages` baut beide Stufen, `--keep-cache`/Cleanup für die
  gemeinsame Cache-Struktur
- Erweiterbarkeit: temporäres drittes Set wird ohne Produktionscodeänderung
  entdeckt, paketiert und als `.lefxset` gebaut

Aktualisiert: `test_architecture.py`, `test_builtin_effects.py`,
`test_effect_tutorials.py`, `conftest.py`. Zusätzlich wurden die
vorbestehenden, durch den Doku-Umbau verursachten Testfehler
(`test_documentation_structure.py`, `test_reset_build_artifacts.py`) behoben.

## 8. Tatsächlich ausgeführte Befehle mit Ergebnissen

| Schritt | Befehl | Ergebnis |
|---|---|---|
| A | `python -m pytest tests/test_effect_building.py tests/test_architecture.py -q` | 25 passed |
| B | `python tools/effect_building/build_lefx.py` | ok, set_count=2, effect_count=57 (34+23) |
| C | `python tools/effect_building/build_lefxset.py --rebuild-packages --keep-cache` | ok, beide .lefxset gebaut + veröffentlicht |
| C (Loader) | beide Sets via `load_effect_set()` geladen | IDs exakt 34/23, package_ids konsistent |
| D | pytest der 7 relevanten Testdateien | grün (nach Behebung der vorbestehenden Doku-/Umgebungsfehler) |
| E | `python -m pytest -q` (Gesamtsuite) | **190 passed, 1 skipped** |
| F | `python tools/effect_building/build_lefxset.py --rebuild-packages` | ok, cache_cleaned=true, Cache entfernt |

## 9. Gebauter Bestand pro Set

| Set | Quellen | Pakete (.lefx) | Set (.lefxset) | Veröffentlicht |
|---|---|---|---|---|
| default-effects | 34 | 34 | `build/output/default-effects.lefxset` | `build/published/default-effects.lefxset` |
| smartspeaker-set | 23 | 23 | `build/output/smartspeaker-set.lefxset` | `build/published/smartspeaker-set.lefxset` |
| **Gesamt** | **57** | **57** | **2** | **2** |

## 10. Nachweis des temporären dritten Sets

`test_third_set_is_discovered_packaged_and_built_without_code_change` legt in
einem temporären Verzeichnis ein minimales Set (`third-set/set.yaml` + eine
gültige State-Quelle) an und weist nach, dass `discover_effect_sets()`,
`build_lefx.py` und `build_lefxset.py` dieses Set automatisch entdecken,
paketieren und als `third-set.lefxset` bauen — ohne jede Änderung an
Produktionscode oder Registry. Der Test ist Teil der grünen Gesamtsuite.

## 11. Bestätigung: Effektinhalte unverändert

`git diff HEAD --find-renames` über `tools/effect_building/sources/` zeigt
ausschließlich Renames mit 0 geänderten Zeilen — mit einer dokumentierten
Ausnahme:

**Explizite Auftraggeber-Anweisung von Marco (2026-08-03):** Zur Auflösung der
Registry-Kollision zwischen Default-Set und Smartspeaker-Set (gleiche lokale
Effekt-IDs `countdown_ring` und `progress_ring` in beiden Sets) wurden die
beiden Overlays im Default-Set umbenannt:

- `countdown_ring` → `countdown_circle`
- `progress_ring` → `progress_circle`

Betroffen: Ordnername, `effect.yaml` (`package_id`), `effect.py`
(`id`-Feld; Renderlogik unverändert), `presets.yaml` (Preset-IDs/Tags),
Runtime-Befehl `src/integrations/application_commands.py` (Countdown-Overlay),
Tests und aktive Doku. Die Smartspeaker-Effekte `countdown_ring` und
`progress_ring` bleiben unverändert.

Damit existieren weiterhin 34 Default- und 23 Smartspeaker-Effektquellen; die
globale ID-Kollision in der EffectRegistry ist aufgelöst.

## 12. Offene Punkte oder Abweichungen

- **Keine offenen Punkte** im Sinne der Definition of Done (siehe unten).
- **Abweichung (auf Anweisung):** Die Umbenennung der zwei Default-Overlays
  (Punkt 11) ist die einzige inhaltliche Änderung an Effektquellen; sie wurde
  von Marco explizit angeordnet und ist hier dokumentiert.
- **Vorbestehend behoben:** Die durch den Commit „Docs aufgeräumt"
  verursachten kaputten Test-/Doku-Pfade (docs/examples → docs/effect_examples,
  docs/archive → docs/.archive) wurden im Zuge dieser Phase repariert, da sie
  den CI-Lauf rot machten. Historische Dokumente in `docs/.archive/` blieben
  unverändert.
- Ein Test der Gesamtsuite ist übersprungen (nicht fehlgeschlagen);
  Abhängigkeit von optional installierter Umgebung.

## Definition of Done — Status

- [x] Beide Sets besitzen ein dauerhaftes `set.yaml`.
- [x] Beide Sets liegen gleichwertig unter `sources/<set-id>/`.
- [x] Es gibt keine Effektquellen mehr direkt unter `sources/states|overlays|events`.
- [x] Alle Sets werden über `sources/*/set.yaml` automatisch entdeckt.
- [x] Es gibt keine Python-Registry der Set-Namen.
- [x] `standard_effects.py` und seine aktive API sind entfernt.
- [x] `build_lefx.py` baut alle gefundenen Sets.
- [x] `build_lefxset.py` baut alle gefundenen Sets.
- [x] Set-Builds verwenden ausschließlich vorgebaute `.lefx`.
- [x] Fehlende, zusätzliche oder fremde Pakete führen zu einem harten Fehler.
- [x] Output und Publish enthalten beide `.lefxset`.
- [x] `build_config.json` entdeckt das gemeinsame Output-Verzeichnis.
- [x] Ein temporäres drittes Set wird ohne Produktionscodeänderung gebaut.
- [x] Kein Effektinhalt wurde verändert (Ausnahme: dokumentierte
      Auftraggeber-Umbenennung, siehe Punkt 11).
- [x] Relevante Tests und Gesamtsuite sind erfolgreich.
- [x] Der Abschlussbericht ist vorhanden und faktisch korrekt.
