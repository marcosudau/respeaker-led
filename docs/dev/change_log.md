# Change Log

## 2026-04-06

### Phase 0 - Baseline Safety Net

- `pytest -q` als wiederholbaren Baseline-Testlauf bestaetigt
- fehlende Service-, Client- und STT-Adapter-Tests ergaenzt
- oeffentliche Einstiegspunkte fuer Runtime, Service, CLI, API und Client dokumentiert

### Phase 1 - Neutralize the Core

- `ControllerRuntime` auf generische Kernkommandos fuer `base_state`, `event`, `countdown`, `direction`, `brightness` und `enabled` umgestellt
- Snapshot und Scene-Namen auf `active_visual` und `event_overlay` konsolidiert
- Event-Queue um Prioritaets-Preemption und saubereres Expiry-Verhalten erweitert

### Phase 2 - Establish Generic Effect / Visual Construction

- generische Primitive in `src/effects.py` als Basis beibehalten
- State-, Event-, Direction- und Countdown-Visuals direkt aus generischen Primitives aufgebaut
- Countdown-Overlay als interne `dynamic_frame`-Animation umgesetzt

### Phase 3 - Core and Service Boundary

- `ControllerService` als aeussere Laufzeithuelle um `ControllerRuntime` eingefuehrt
- Worker-Thread, Lifecycle und Fallback-Verhalten aus dem Core herausgezogen
- Service faellt bei fehlender Hardware sicher auf Console-Preview zurueck

### Phase 4 - Local API Around Generic Commands

- FastAPI-Routen auf generische Controller-Kommandos umgestellt
- `ping`, `status`, `set_state`, `emit_event`, Countdown-, Direction-, Brightness- und Enabled-Kommandos eingefuehrt
- optionale Preset-Aktivierung unter eigener, kleiner API-Oberflaeche behalten

### Phase 5 - CLI Around Generic Controller Usage

- `serve-api`, `push-event`, `progress` und `render-preset` aus der oeffentlichen CLI entfernt
- CLI jetzt sowohl fuer `serve` als auch fuer Kommandos an den laufenden lokalen Service nutzbar
- generischer Demo-Modus fuer Preview-Smoketests erhalten

### Phase 6 - Best-Effort Client and Thin STT Adapter

- `LocalControllerClient` als lokale Best-Effort-Kommandoschicht eingefuehrt
- `SttLedAdapter` mappt Recorder-/STT-Hooks auf generische LED-Kommandos
- keine STT-spezifische Logik in den Runtime-Core gezogen

### Phase 7 - Optional Discovery Refactor

- optionale Preset-/Effekt-Pack-Discovery beibehalten
- Standardziel auf `active_visual` ausgerichtet
- Core bleibt ohne Discovery voll funktionsfaehig

### Phase 8 - Cleanup and Final Stabilization

- veraltete Layer-first-Routen und CLI-Kommandos aus aktiven Codepfaden entfernt
- Tests und Dokumentation auf die neue Terminologie umgestellt
- verbleibende Legacy-Marker in `src/` ueber Architekturtests abgesichert

### Phase 9 - Final Validation and Handover

- komplette Test-Suite gruen
- Preview-Smoke-Test und lokaler Service-/Prozess-Smoke-Test vorgesehen und dokumentiert
- Migrationszusammenfassung und bewusst verschobene Arbeit festgehalten

## Migration Summary

- Der Kern wird jetzt ueber `ControllerRuntime` mit generischen Kommandos statt ueber layer-zentrierte API/CLI-Surfaces angesteuert.
- Der lokale Prozess laeuft ueber `ControllerService` und exponiert nur Kommandos und Status, nicht die innere Effektlogik.
- Externe Aufrufer nutzen `LocalControllerClient`; STT-Integrationen sitzen in `SttLedAdapter` ueber dieser Client-Schicht.
- Optionale Effekt-Packs bleiben moeglich, sind aber nicht laenger das Zentrum der Architektur.

## Intentionally Deferred

- fortgeschrittene Overlay- oder Blend-Strategien
- ein vollstaendiges YAML-/JSON-Domain-Specific-Language-Layer
- verteilte oder nicht-lokale API-Steuerung
- produkt-spezifische STT-UX-Politur

---

### Phase 10 - Effects Engine: Erweiterte Per-LED-Effekte

- `LedRingBackend` um `set_ring_colors(colors: list[RGB])` erweitert
- `LED_COUNT = 12` als Konstante in `backend.py` eingefuehrt
- 6 neue per-LED-Effekte in `advanced_effects.py`:
  - `CustomDoaEffect` – Software-DoA mit 3-LED-Zeiger und Live-Provider
  - `TimerCountdownEffect` – Countdown-Ring mit Sub-LED-Dimming und Farbzonen
  - `ProgressRingEffect` – Fortschrittsanzeige mit ~96-Stufen-Aufloesung
  - `SpinnerEffect` – Rotierende Punkte mit Kometenschweif
  - `PulseWaveEffect` – Gauss-Helligkeitswelle ueber den Ring
  - `SegmentMeterEffect` – VU-Meter mit Gruen/Gelb/Rot-Zonen
- Config-Loader um 6 neue Builder erweitert (Typen: `custom_doa`, `timer`, `progress`, `spinner`, `pulse_wave`, `segment_meter`)
- Standard-Bibliothek um 7 neue Presets erweitert (4 States, 3 Timer-Events)
- 47 neue Tests in `test_advanced_effects.py` (Gesamt: 189 Tests)
- Benutzer-Dokumentation: `docs/effects_engine.md`
- Entwickler-Dokumentation: `docs/dev/effects_engine_dev.md`
- RecordingBackend, DryRunBackend und XvfHostBackend um `set_ring_colors()` erweitert
