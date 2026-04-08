# Development Notes

## Ziel der aktuellen Architektur

Der Core soll ein generischer LED-Effekt-Engine-Kern sein und keine App-Semantik tragen.

Dafuer gelten folgende Leitlinien:

- der Core exponiert generische Kommandos fuer `base_state`, `event`, `countdown` und `direction`
- `ControllerRuntime` bleibt die Source of Truth fuer Effektlogik und Zustandsmodell
- `ControllerService` kuemmert sich nur um Worker, API, Prozess-Lifecycle und Fallbacks
- primitive Effekte leben in `src/effects.py`
- Discovery ist optional und laeuft ueber Preset-Packs
- `SceneComposer`, `SceneRenderer` und `FrameAdapter` bleiben die stabile Pipeline
- Hardware-Ausgabe bleibt auf Vollring-Frames fuer den ReSpeaker ausgelegt

## Preset-Discovery

Preset-Packs liegen unter `led_effects/preset_packs/<name>/`.

Ein Pack besitzt mindestens:

- `preset.yaml`
- `preset.py`

Optional:

- `sample.json`

`preset.py` exportiert `build_preset(spec)` und gibt `PresetBuildResult` zurueck.

## API und CLI

API und CLI arbeiten beide gegen denselben `ControllerRuntime`, aber nur ueber den aeusseren `ControllerService`.

Die API bleibt bewusst klein und deckt nur die generischen Kernaktionen ab:

- Status lesen und Service pingen
- Basiszustand setzen oder zuruecksetzen
- Events ausloesen
- Countdown starten, aktualisieren und abbrechen
- Richtung, Brightness und Enabled setzen
- Presets optional laden und aktivieren

## Lokale Integrationen

- Externe Prozesse verwenden `LocalControllerClient`.
- STT-Integrationen laufen ueber `SttLedAdapter` und bleiben ausserhalb des Cores.
- Best-Effort ist fuer externe Aufrufer Standard; nur CLI-Kommandos schalten auf striktes Fehlerverhalten um.

## Bewusst verschoben

- YAML-/JSON-DSL oberhalb einzelner Presets
- fortgeschrittene Blend-/Overlay-Strategien
- app-spezifische Semantik-Mappings

## Effects Engine (led_effects/effects_engine/)

Eigenstaendiges Subsystem fuer Echtzeit-LED-Steuerung:

- **Basis-Effekte** (9): Ganze-Ring-Kommandos (off, static, breath, rainbow, doa, blink, alternate, fade, sequence)
- **Erweiterte Effekte** (6): Per-LED-Steuerung via `set_ring_colors()`:
  - `CustomDoaEffect`, `TimerCountdownEffect`, `ProgressRingEffect`
  - `SpinnerEffect`, `PulseWaveEffect`, `SegmentMeterEffect`
- Thread-sicherer `LedRingController` mit State/Event-Kanaelen
- Deklarative Konfiguration per Dict/JSON/YAML (15 Effekt-Typen)
- 26 Standard-Presets in `stdlib.py`
- `LED_COUNT = 12` in `backend.py`, genutzt von allen per-LED-Effekten

Technische Details: siehe `docs/dev/effects_engine_dev.md`
