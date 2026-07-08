# Bericht 1: Hauptlogik des LED-Controller-Programms

Stand: 2026-07-08  
Untersuchter Arbeitsbaum: `C:\Users\marco\OneDrive\Desktop\Respeaker_MaterialCheck\led_controller_respeaker`  
Aktueller Branch laut Git: `codex/develop-branch`

## Kurzfazit

Diese Version ist kein kleiner Demo-Controller mehr, sondern ein lokaler Service fuer einen framebasierten LED-Ring. Der aktive Produktpfad laeuft ueber `main.py`, CLI/API, `ControllerService`, `ControllerRuntime`, LayerStore, Composer, Renderer und FrameAdapter. Die Hauptlogik ist weitgehend von den Effektdefinitionen getrennt: Die Runtime kennt Effektklassen nur ueber eine Registry und laedt die Default-Effekte aus gebauten `.lefxset`/`.lefx`-Artefakten.

Der Gesamtzustand ist strukturiert und testnah, aber nicht ganz sauber: Es gibt staged Aenderungen im Git-Index, die aktuell einen Test brechen. Ausserdem ist die Git-/Worktree-Situation tatsaechlich unuebersichtlich: dieser Ordner ist ein Worktree, dessen `.git` auf `P:/CodexApp/led_controller_respeaker/.git/worktrees/led_controller_respeaker3` zeigt.

## Einstiegspunkte

Die aktiven Einstiegspunkte sind:

- `main.py`: fuegt Projektwurzel und `src` zum `sys.path` hinzu und ruft `src.interfaces.cli.main()` auf.
- `src/__main__.py`: alternativer Start ueber `python -m src`.
- `src/interfaces/cli.py`: CLI-Parser, Service-Start, Client-Kommandos und Uvicorn-Hosting.
- `src/interfaces/api.py`: FastAPI-App mit HTTP-Endpunkten.
- `src/services/service.py`: Thread-sicherer Service um die Runtime herum.
- `src/engine/runtime.py`: zentrale Controller-Logik.

Der normale Nutzerpfad ist:

```text
CLI / HTTP / STT-Adapter
-> ControllerService
-> ControllerRuntime
-> ControllerCommandNormalizer
-> EffectInvocation
-> LayerStore
-> SceneComposer
-> SceneRenderer
-> FrameAdapter
```

## Zentrale Module und Verantwortlichkeiten

`src/core/models.py` definiert die einfachen Laufzeitmodelle: `BaseState`, `CountdownState`, `Scene`, `Frame`, `Visual` und die feste LED-Anzahl `LED_COUNT = 12`.

`src/core/effect_schema.py` definiert die Effekt- und Layer-Kontrakte: `LayerId`, `PlaybackMode`, `LayerRule`, `EffectDefinition`, `EffectInvocation`, `RenderContext` und `BaseEffect`. Das ist die wichtigste Schnittstelle zwischen Hauptlogik und Effektlogik.

`src/core/layers.py` verwaltet den aktuellen Zustand aller Layer. Es gibt sechs Layer:

- `BACKGROUND_STATE_LAYER`
- `STATE_LAYER`
- `MAIN_LAYER`
- `TEMP_OVERLAY_LAYER`
- `ONGOING_OVERLAY_LAYER`
- `EVENT_LAYER`

Jeder Layer hat Prioritaet, aktive Invocation, Queue und Metadaten wie `scene_name`, `item_id`, `mode`, `payload` und `valid`.

`src/engine/normalization.py` uebersetzt fachliche Kommandos in normalisierte Effekt-Kommandos. Beispiele:

- `set_state("idle")` setzt einen Hintergrund und leert den State-Layer.
- `set_state("recording")` setzt Hintergrund plus `soft_pulse` auf dem State-Layer.
- `emit_event("error_flash")` erzeugt einen priorisierten Event-Layer-Effekt.
- `set_direction()` erzeugt einen `direction_indicator`.
- `start_timeout_countdown()` erzeugt einen `countdown_ring`.
- `set_progress()` kombiniert State-Logik mit `progress_bar`.

`src/engine/runtime.py` ist die eigentliche Orchestrierung. Sie haelt Registry, Normalizer, LayerStore, Composer, Renderer und Adapter zusammen. Sie setzt Zustaende, Events, Countdown, Richtung, Helligkeit und Enabled-Status und rendert Frames.

`src/engine/composer.py` baut aus dem LayerStore eine Scene. Die Composer-Schicht instanziiert den registrierten Effekt und ruft dessen `render(ctx)` auf.

`src/engine/renderer.py` rendert aktuell nur `dynamic_frame`-Visuals. Layer werden in Prioritaetsreihenfolge ueberlagert. `None` bedeutet transparent, ein Integer ist eine LED-Farbe. Wenn `main_layer_valid` false ist, wird eine einfache Diagnose-LED ueberlagert.

`src/integrations/adapters.py` kapselt die Ausgabe:

- `ConsolePreviewAdapter`
- `MemoryFrameAdapter`
- `ReSpeakerAdapter`

Der echte Hardwareadapter laedt `src/python_control/xvf_host.py`, sucht das ReSpeaker-Geraet, setzt den Ringmodus und schreibt `LED_RING_COLOR`.

## Service- und API-Verhalten

`ControllerService` kapselt die Runtime mit Locking und Render-Thread. Wichtige Service-Funktionen:

- Renderloop mit konfigurierbarer FPS.
- Start-/Stop-Signal per dreimaligem Vollring-Blink.
- Fallback auf Console Preview, wenn das echte Geraet nicht verfuegbar ist.
- Wiederherstellung eines persistierten Background-State.
- Snapshot-/Statusausgabe mit Runtime-, Adapter- und Service-Metadaten.
- Thread-sichere Mutationsmethoden fuer alle Kommandos.

Die FastAPI-App bietet unter anderem:

- `/health`
- `/api/v1/ping`
- `/api/v1/status`
- `/api/v1/effects`
- `/api/v1/effect-sources`
- `/api/v1/effect-presets/...`
- `/api/v1/commands/set_state`
- `/api/v1/commands/emit_event`
- `/api/v1/commands/apply_effect`
- `/api/v1/commands/start_timeout_countdown`
- `/api/v1/commands/set_direction`
- `/api/v1/commands/set_brightness`
- `/api/v1/commands/set_enabled`

Die CLI spiegelt diese Funktionen als Kommandos wie `serve`, `ping`, `status`, `list-effects`, `apply-effect`, `set-state`, `emit-event`, `start-countdown`, `set-direction`, `shutdown` usw.

## Implementierte Features der Hauptlogik

Fachliche Runtime-Features:

- Basiszustaende: `offline`, `idle`, `listening`, `recording`, `transcribing`, `error`, `service_starting`, `service_stopping`, `wakeword_armed`, `wakeword_detected`, `ready`, `processing`, `muted`, `realtime_active`.
- Events: `trigger_received`, `text_committed`, `warning`, `error_flash`, `timeout_imminent`, `wakeword_ack`, `notification`.
- Countdown mit Deadline, Follow-up-State und Aktualisierung.
- Richtungsmarker fuer DoA-/Direction-Use-Cases.
- Fortschrittsanzeige.
- Helligkeitsregelung.
- Globales Output-Enable/Disable.
- Einzelne Layer gezielt leeren.
- Direkte Effektanwendung auf beliebige erlaubte Layer.
- Presets und Commands aus Effektpaketen anwenden.
- Priorisierte Event-Queue.
- Status-Snapshot fuer Host-Anwendungen.

Service-/Betriebsfeatures:

- Lokaler FastAPI-Service mit Uvicorn.
- CLI-Client fuer laufenden Service.
- Portpool und Portverfuegbarkeitspruefung.
- Uebernahme einer alten aktiven Instanz per `active_service.json`.
- `active_service.json` als Rueckkanal fuer Host/Port/PID.
- Persistenz fuer `BACKGROUND_STATE_LAYER` in `background_state.json`.
- Geraete-Fallback ohne harten Startabbruch.
- Logging unter `logs/`.

Integrationsfeatures:

- `SttLedAdapter` fuer STT-Lifecycle-Callbacks.
- Low-Level-ReSpeaker-Zugriff unter `src/python_control/`.
- Build-/Release-Tooling unter `build-tools/`.

## Persistenz und Runtime-Dateien

Zur Laufzeit schreibt der Service in das Temp-Verzeichnis:

```text
respeaker_led_controller_runtime_state/
```

Dort liegen:

- `background_state.json`
- `active_service.json`
- `effect_package_cache/`

Der aktive Background-State wird nur persistiert, wenn der Effekt fuer `BACKGROUND_STATE_LAYER` persistent erlaubt ist und die Parameter serialisierbar sind.

## Build- und Release-Bezug

`build-tools/build_config.json` steuert den normalen Build. Wichtige Schalter:

- `build_effects: true`
- `build_exe: true`
- `build_release_bundle: true`
- `cleanup: true`
- `builtin-effects-discovery`: verweist auf die gebauten Effektartefakte unter `tools/effect_building/build/...`

Das normale Build-System konsumiert fertige Effektartefakte. Es ist nicht selbst der Ort, an dem Effektdefinitionen fachlich gepflegt werden.

## Git- und Branch-Befund

Der aktuelle Arbeitsbaum ist auf:

```text
codex/develop-branch...origin/codex/develop-branch
```

Aktuelle Branch-Situation:

- `main` steht bei `efe6ebf` und entspricht `origin/main`.
- `codex/effekt-dateien` steht bei `5b43937`.
- `codex/develop-branch` steht bei `0fae51c` und entspricht `origin/codex/develop-branch`.
- `codex/develop-branch` ist 9 Commits vor `origin/main`.
- `codex/develop-branch` ist 22 Commits vor `origin/codex/effekt-dateien`.

Worktree-Befund:

```text
.git -> P:/CodexApp/led_controller_respeaker/.git/worktrees/led_controller_respeaker3
```

`git worktree list` zeigt mehrere Worktrees und detached HEADs. Das erklaert wahrscheinlich die Erinnerung an unterschiedliche Branches oder Staende. Dieser konkrete Ordner ist nicht das Haupt-Checkout unter `P:/CodexApp/led_controller_respeaker`, sondern ein verknuepfter Worktree.

Aktuell staged, aber nicht committet:

- `.gitignore`
- `build-tools/scripts/create_release_bundle.py`
- `src/__init__.py`
- `tests/build_artifact_helpers.py`

Diese staged Aenderungen sind relevant, weil sie aktuell mindestens einen Test brechen.

## Validierung

Ausgefuehrte Pruefungen:

- `uv run python tools/effect_packager.py verify-effect-package tools\effect_building\build\build_lefxset\default-effects.lefxset`
  - Ergebnis: erfolgreich.
  - Das Effektset enthaelt 37 Effekte und 148 Commands.
- Runtime-Registry geladen per `build_default_effect_registry()`
  - Ergebnis: 37 Effekte, 148 Presets, 148 Commands.
- `uv run pytest -q --basetemp=.pytest_tmp`
  - Ergebnis: `115 passed, 1 failed`.

Der fehlgeschlagene Test:

```text
tests/test_release_tooling.py::test_create_release_bundle_replaces_existing_zip_without_force
```

Ursache: Der staged Code in `build-tools/scripts/create_release_bundle.py` wirft bei vorhandenem ZIP ohne `force=True` jetzt `FileExistsError`. Der Test erwartet noch das alte Verhalten: vorhandenes ZIP wird ohne Force ersetzt. Das ist eine echte Inkonsistenz zwischen Code und Test, nicht nur ein Analyseproblem.

## Gesamt-Einschaetzung

Architektonisch ist die Hauptlogik fuer ein kleines Hardwaretool erstaunlich sauber geschichtet. Besonders positiv ist die klare Pipeline von Kommando-Normalisierung ueber LayerStore bis Renderer und Adapter. Auch die Trennung zwischen Service/Runtime und Effektartefakten ist real implementiert, nicht nur dokumentiert.

Die Codequalitaet wirkt insgesamt solide: viele kleine Module, dataclass-basierte Modelle, gute Testabdeckung und klare Servicegrenzen. Die Tests decken API, CLI, Runtime, Renderer, Registry, Packaging und Build-Tooling ab.

Die groessten Risiken liegen aktuell nicht im Kernmodell, sondern im Repository-Zustand:

- staged Aenderungen ohne Commit;
- mindestens ein Testkonflikt durch diese staged Aenderungen;
- mehrere Worktrees und alte Branches;
- Build-Artefakte und generierte Effektquellen sind funktional wichtig, koennen aber leicht mit Quelllogik verwechselt werden.

Technisch ist diese Version klar weiterentwickelt als eine fruehe, gemischte Script-Version. Der aktuelle Stand ist brauchbar und gut testbar, aber vor neuer Featurearbeit sollte zuerst entschieden werden, ob die staged Release-Tooling-Aenderung korrekt ist. Danach muss entweder der Test angepasst oder das alte Verhalten wiederhergestellt werden.
