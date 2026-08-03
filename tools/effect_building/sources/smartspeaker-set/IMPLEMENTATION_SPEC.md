# Smartspeaker-Effektset – Umsetzungsspezifikation v1

## 1. Setweite Festlegungen

- **source_id:** `smartspeaker-set`
- **package_id:** `smartspeaker-set.<effect_id>`
- **Definition-ID / Ordnername:** exakt der vom Auftraggeber vorgegebene Slug
- **Preset-IDs:** `<effect_id>_<variant>`

- **Quellstruktur:** `tools/effect_building/sources/smartspeaker-set/<states|overlays|events>/<effect_id>/`
- **States:** ausschließlich `STATE_LAYER`, opaque, sofern unten nicht anders festgelegt
- **Overlays:** transparent, wenn der darunterliegende State sichtbar bleiben soll; `loading_spinner` bewusst opaque
- **Events:** endliche `SINGLE_RUN`-Effekte mit `duration_ms`
- **Zeitanimation:** immer aus `ctx.now - ctx.invocation.created_at`, nie aus Framezählern
- **LED-Anzahl:** immer `ctx.led_count`, nie fest auf 12 verdrahten
- **Parameter:** nur fachlich sinnvolle Regler; alle Längen werden im Renderer auf `ctx.led_count` begrenzt

## 2. States

### 2.1 `ready_state` – Bereit / Idle

- **Klasse:** `ReadyState`
- **Darstellung:** sanfter Vollring-Atemeffekt
- **Farbmodell:** `MONO`
- **animated / directional:** `True / False`
- **Parameter:** `color`, `brightness`, `speed`, `min_brightness`
- **Defaults:** Grün, `brightness=0.55`, `speed=0.45`, `min_brightness=0.16`
- **Presets:** `soft_green`, `calm_blue`

### 2.2 `waiting` – Wartend

- **Klasse:** `WaitingState`
- **Darstellung:** einzelner langsam rotierender Punkt, übriger Ring schwarz
- **Farbmodell:** `MONO`
- **animated / directional:** `True / True`
- **Parameter:** `color`, `brightness`, `speed`, `reverse`
- **Defaults:** Cyan, `brightness=0.70`, `speed=0.28`, `reverse=False`
- **Presets:** `slow_cyan`, `slow_blue`

### 2.3 `processing` – Verarbeitung

- **Klasse:** `ProcessingState`
- **Darstellung:** mehrere gleichmäßig verteilte Punkte rotieren gemeinsam
- **Farbmodell:** `MONO`
- **animated / directional:** `True / True`
- **Parameter:** `color`, `brightness`, `speed`, `reverse`, `point_count`
- **Defaults:** Blau, `brightness=0.85`, `speed=0.90`, `point_count=3`
- **Presets:** `balanced_blue`, `fast_blue`

### 2.4 `reconnect_network_state` – Netzwerk-Reconnect

- **Klasse:** `ReconnectNetworkState`
- **Darstellung:** alternierende helle und dunkle gelbe LEDs atmen gemeinsam
- **Farbmodell:** `DUAL`
- **animated / directional:** `True / False`
- **Parameter:** `color`, `secondary_color`, `brightness`, `speed`, `min_brightness`
- **Defaults:** Hellgelb / Dunkelgelb, `brightness=0.85`, `speed=0.42`, `min_brightness=0.20`
- **Presets:** `standard_yellow`, `subtle_yellow`

### 2.5 `reconnect_mic_state` – Mikrofon-/Hardware-Reconnect

- **Klasse:** `ReconnectMicState`
- **Darstellung:** alternierende helle und dunkle orange LEDs atmen gemeinsam
- **Farbmodell:** `DUAL`
- **animated / directional:** `True / False`
- **Parameter:** `color`, `secondary_color`, `brightness`, `speed`, `min_brightness`
- **Defaults:** Hellorange / Dunkelorange, `brightness=0.88`, `speed=0.46`, `min_brightness=0.20`
- **Presets:** `standard_orange`, `subtle_orange`

### 2.6 `listening` – Zuhören

- **Klasse:** `ListeningState`
- **Darstellung:** ruhiger Cyan-Vollring-Atemeffekt
- **Farbmodell:** `MONO`
- **animated / directional:** `True / False`
- **Parameter:** `color`, `brightness`, `speed`, `min_brightness`
- **Defaults:** Cyan, `brightness=0.68`, `speed=0.65`, `min_brightness=0.22`
- **Presets:** `calm_cyan`, `calm_blue`

### 2.7 `transcribe` – Verstehen / Transkription

- **Klasse:** `TranscribeState`
- **Darstellung:** heller fokussierter Kopf mit kurzem weichem Schweif rotiert zügig
- **Farbmodell:** `MONO`
- **animated / directional:** `True / True`
- **Parameter:** `color`, `brightness`, `speed`, `reverse`, `trail_length`, `falloff`
- **Defaults:** Blau, `brightness=0.95`, `speed=1.35`, `trail_length=4`, `falloff=0.62`
- **Presets:** `focused_blue`, `fast_blue`

### 2.8 `thinking` – Antwort wird erzeugt

- **Klasse:** `ThinkingState`
- **Darstellung:** breiter, weich auslaufender Sweep läuft gleichmäßig um den Ring
- **Farbmodell:** `MONO`
- **animated / directional:** `True / True`
- **Parameter:** `color`, `brightness`, `speed`, `reverse`, `width`, `falloff`
- **Defaults:** Lila, `brightness=0.76`, `speed=0.48`, `width=5`, `falloff=0.55`
- **Presets:** `purple_sweep`, `blue_sweep`

### 2.9 `speaking` – Audioausgabe aktiv

- **Klasse:** `SpeakingState`
- **Darstellung:** mehrere symmetrische Segmente pulsieren rhythmisch mit versetzten Phasen
- **Begründete Auswahl:** selbstlaufende rhythmische Segmente statt Audio-Reaktivität, damit der State ohne externe Laufzeitwerte vollständig autark bleibt
- **Farbmodell:** `MONO`
- **animated / directional:** `True / False`
- **Parameter:** `color`, `brightness`, `speed`, `min_brightness`, `segment_length`
- **Defaults:** Cyanblau, `brightness=0.90`, `speed=1.25`, `min_brightness=0.18`, `segment_length=2`
- **Presets:** `rhythmic_cyan`, `rhythmic_blue`

### 2.10 `mic_mute` – Mikrofon stumm

- **Klasse:** `MicMuteState`
- **Darstellung:** statisches rotes, vierfach symmetrisches X-artiges Ringmuster
- **Farbmodell:** `MONO`
- **animated / directional:** `False / False`
- **Parameter:** `color`, `brightness`, `segment_length`
- **Defaults:** Rot, `brightness=0.90`, `segment_length=1`
- **Presets:** `clear_red`, `dim_red`

## 3. Overlays

### 3.1 `progress_ring` – Fortschritt

- **Klasse:** `ProgressRingOverlay`
- **Modus:** `CONTROLLED`
- **Komposition:** transparent
- **Darstellung:** Ringfüllung proportional zum laufend gelieferten Fortschrittswert
- **Farbmodell:** `MONO`
- **animated / directional:** `False / True`
- **Konfigurationsparameter:** `color`, `brightness`, `reverse`
- **Runtime-Eingabe:** `progress` als `float`, `0.0..100.0`, Einheit `percent`
- **Presets:** `green_progress`, `blue_progress`

### 3.2 `loading_spinner` – Ladevorgang

- **Klasse:** `LoadingSpinnerOverlay`
- **Modus:** `CONTROLLED`
- **Komposition:** opaque
- **Darstellung:** heller rotierender Abschnitt auf dunklem Vollring-Hintergrund
- **Farbmodell:** `DUAL`
- **animated / directional:** `True / True`
- **Parameter:** `color`, `secondary_color`, `brightness`, `speed`, `reverse`, `segment_length`
- **Runtime-Eingaben:** keine; Aufrufer setzt und entfernt den Channel
- **Defaults:** Hellcyan / sehr dunkles Blau, `speed=0.85`, `segment_length=3`
- **Presets:** `cyan_spinner`, `blue_spinner`

### 3.3 `countdown_ring` – Countdown / Timer

- **Klasse:** `CountdownRingOverlay`
- **Modus:** `TIMED`
- **Komposition:** transparent
- **Darstellung:** zunächst voller Ring, der sich bis zum Ende leert; Farbe wechselt Grün → Gelb → Rot; im letzten Abschnitt pulsiert der Rest schneller
- **Farbmodell:** `PALETTE`
- **animated / directional:** `False / True`
- **Parameter:** `colors`, `brightness`, `duration_ms`, `reverse`
- **Defaults:** Grün/Gelb/Rot, `brightness=0.90`, `duration_ms=10000`
- **Presets:** `traffic_light_10s`, `traffic_light_30s`

### 3.4 `timeout_segment` – Warten auf Timeout

- **Klasse:** `TimeoutSegmentOverlay`
- **Modus:** `TIMED`
- **Komposition:** transparent
- **Darstellung:** ein Segment schrumpft weich und unaufgeregt bis auf null
- **Farbmodell:** `MONO`
- **animated / directional:** `False / True`
- **Parameter:** `color`, `brightness`, `duration_ms`, `reverse`, `segment_length`
- **Defaults:** Warmgelb, `brightness=0.72`, `duration_ms=5000`, `segment_length=6`
- **Presets:** `gentle_yellow_5s`, `gentle_cyan_10s`

## 4. Events

Alle Events verwenden `duration_ms`, `SINGLE_RUN` und standardmäßig **kein Duration-Override**, damit ihre kuratierten Abläufe reproduzierbar bleiben.

### 4.1 `init_event` – Initialisierung / Start

- **Klasse:** `InitEvent`
- **Komposition:** opaque
- **Darstellung:** Ring füllt sich vollständig; am Ende kurzer Weißblitz
- **Farbmodell:** `DUAL`
- **Parameter:** `color`, `secondary_color`, `brightness`, `duration_ms`
- **Defaults:** Blau / Weiß, `duration_ms=1400`
- **Presets:** `startup_blue`, `startup_cyan`

### 4.2 `connected_event` – Verbunden

- **Klasse:** `ConnectedEvent`
- **Komposition:** transparent
- **Darstellung:** kurzer grüner Rundlauf mit sanftem Ausblenden
- **Farbmodell:** `MONO`
- **Parameter:** `color`, `brightness`, `duration_ms`, `reverse`, `trail_length`
- **directional:** `True`
- **Defaults:** Grün, `duration_ms=750`, `trail_length=4`
- **Presets:** `connected_green`, `connected_cyan`

### 4.3 `success_event` – Erfolg

- **Klasse:** `SuccessEvent`
- **Komposition:** opaque
- **Darstellung:** ein kurzer weicher grüner Vollring-Impuls
- **Farbmodell:** `MONO`
- **Parameter:** `color`, `brightness`, `duration_ms`
- **Defaults:** Grün, `duration_ms=520`
- **Presets:** `success_green`, `success_soft`

### 4.4 `error_event` – Fehler

- **Klasse:** `ErrorEvent`
- **Komposition:** opaque
- **Darstellung:** zwei bis drei schnelle rote Pulse; optional zweite Pulsgruppe nach kurzer Pause
- **Farbmodell:** `MONO`
- **Parameter:** `color`, `brightness`, `duration_ms`, `pulse_count`, `repeat_count`
- **Defaults:** Rot, `duration_ms=900`, `pulse_count=3`, `repeat_count=1`
- **Presets:** `error_standard`, `error_critical`

### 4.5 `warn_event` – Warnung

- **Klasse:** `WarnEvent`
- **Komposition:** opaque
- **Darstellung:** langsameres, weicheres gelbes Blinken
- **Farbmodell:** `MONO`
- **Parameter:** `color`, `brightness`, `duration_ms`, `pulse_count`
- **Defaults:** Gelb, `duration_ms=1000`, `pulse_count=2`
- **Presets:** `warning_yellow`, `warning_soft`

### 4.6 `notification_event` – Neue Benachrichtigung

- **Klasse:** `NotificationEvent`
- **Komposition:** transparent
- **Darstellung:** kurzer freundlicher Sweep mit weichem Schweif
- **Farbmodell:** `MONO`
- **Parameter:** `color`, `brightness`, `duration_ms`, `reverse`, `trail_length`
- **directional:** `True`
- **Defaults:** Cyan, `duration_ms=850`, `trail_length=5`
- **Presets:** `notification_cyan`, `notification_purple`, `notification_white`

### 4.7 `confirm_event` – Bestätigung

- **Klasse:** `ConfirmEvent`
- **Komposition:** opaque
- **Darstellung:** ein kurzer, weicher grüner Puls
- **Farbmodell:** `MONO`
- **Parameter:** `color`, `brightness`, `duration_ms`
- **Defaults:** Grün, `duration_ms=380`
- **Presets:** `confirm_green`, `confirm_soft`

### 4.8 `reject_event` – Ablehnung

- **Klasse:** `RejectEvent`
- **Komposition:** opaque
- **Darstellung:** sofortiger roter Gegenschlag: kräftiger Beginn, rascher Abfall und kurzer inverser Nachimpuls
- **Farbmodell:** `MONO`
- **Parameter:** `color`, `brightness`, `duration_ms`
- **Defaults:** Rot, `duration_ms=460`
- **Presets:** `reject_red`, `reject_soft`

### 4.9 `wakeword_detected` – Sprache erkannt

- **Klasse:** `WakewordDetectedEvent`
- **Komposition:** opaque
- **Darstellung:** kurzer reaktiver Cyan-Vollringblitz mit sehr schnellem Ein- und weichem Ausblenden
- **Begründete Auswahl:** Cyan-Blitz statt Pegelanzeige, weil ein Event einen abgeschlossenen Ablauf ohne laufende Runtime-Eingaben besitzt
- **Farbmodell:** `MONO`
- **Parameter:** `color`, `brightness`, `duration_ms`
- **Defaults:** Cyan, `duration_ms=300`
- **Presets:** `wakeword_cyan`, `wakeword_blue`

## 5. Vorgesehene Produktionsreihenfolge

1. Atem- und Puls-States: `ready_state`, `listening`, beide Reconnect-States
2. Rotations-States: `waiting`, `processing`, `transcribe`, `thinking`
3. Sonder-States: `speaking`, `mic_mute`
4. Controlled Overlays: `progress_ring`, `loading_spinner`
5. Timed Overlays: `countdown_ring`, `timeout_segment`
6. Positive Events: `init_event`, `connected_event`, `success_event`, `confirm_event`, `wakeword_detected`
7. Negative und neutrale Events: `error_event`, `warn_event`, `notification_event`, `reject_event`

## 6. Prüfmatrix

Für jeden Effekt mindestens:

- Python-Syntax
- Source-Validierung
- Paketbau und Paketverifikation
- Renderframes bei `led_count=12` und mindestens einer abweichenden LED-Anzahl
- Start und späterer Zeitpunkt
- Anfang/Mitte/Ende bei Timed Overlays und Events
- Min-/Max-Parameter
- Ringumbruch
- `reverse=False/True`, sofern vorhanden
- vollständige Framelänge
- transparente/opaque Komposition gemäß Definition
- Preset-Auflösung
- Controlled Runtime-Werte bei Minimum, Mitte und Maximum

