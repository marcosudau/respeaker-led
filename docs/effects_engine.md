# Welche Anzeigen Es Gibt

Diese Seite beschreibt die Effects Engine aus Nutzersicht.

Nicht: welche interne Klasse was genau tut.
Sondern: welche Arten von Anzeigen du ueberhaupt bauen kannst.

Wenn du direkt loslegen willst:

- [LEDs in 2 Minuten anzeigen](effects_engine_2_minuten.md)
- [Eigene Anzeigen Schritt fuer Schritt](effects_engine_tutorial.md)

## Die Grundidee

Mit der Effects Engine kannst du dem Ring verschiedene Arten von Anzeigen geben:

- Farbe
- Bewegung
- kurze Rueckmeldung
- Countdown
- Fortschritt
- Richtung
- Pegel

Wie das intern umgesetzt wird, ist fuer die Nutzung erstmal egal.

## Anzeigen Nach Zweck

### 1. Einfache Daueranzeigen

Wenn du einfach einen Zustand sichtbar machen willst:

- feste Farbe
- Atmen
- Regenbogen

Typische Beispiele:

- `idle`
- `listening`
- `muted`

### 2. Kurze Rueckmeldungen

Wenn etwas einmal kurz sichtbar aufblinken soll:

- Blinken
- Farbwechsel
- kleine Sequenzen

Typische Beispiele:

- `success`
- `warning`
- `error`
- `notification`

### 3. Bewegte Aktivitaetsanzeigen

Wenn sichtbar sein soll, dass gerade etwas arbeitet:

- Spinner
- doppelte Spinner
- wandernde Welle

Typische Beispiele:

- `processing`
- `spinner`
- `pulse_wave`

### 4. Zeit und Fortschritt

Wenn nicht nur Licht, sondern Information angezeigt werden soll:

- Countdown
- Fortschrittsring

Typische Beispiele:

- Aufnahmefenster
- Timeout
- Upload- oder STT-Fortschritt

### 5. Richtung und Pegel

Wenn die Anzeige von Messwerten lebt:

- Richtungshinweis
- Richtungszeiger
- Pegelanzeige

Typische Beispiele:

- Sprecher-Richtung
- Audiolevel
- Auslastung oder Messwerte

## Drei Wege, Diese Anzeigen Zu Benutzen

### Direkt in Python

Der schnellste Weg.

Gut fuer:

- sofort etwas anzeigen
- Live-Werte
- schnelle Skripte

### Per JSON/YAML

Gut fuer:

- feste Definitionen
- wiederverwendbare Effektsets
- einfache Konfiguration ohne neue Python-Klassen

Wichtig:

- JSON/YAML werden lokal geladen
- JSON/YAML werden nicht an die API geschickt

### Per CLI/API

Gut fuer:

- einen laufenden Controller fernsteuern
- externe Tools oder Prozesse anbinden

## Was du dafuer nicht wissen musst

Diese internen Unterschiede sind fuer Nutzer normalerweise nicht wichtig:

- ob ein Effekt intern jede LED einzeln setzt
- welche Klasse unter der Haube verwendet wird
- welche Threads oder Locks beteiligt sind

Genau diese Themen sind in die Dev-Doku verschoben.

## Standardnamen, die du direkt benutzen kannst

### States

- `state_idle`
- `state_waiting`
- `state_processing`
- `state_connecting`
- `state_offline`
- `state_muted`
- `state_listening`
- `state_thinking`
- `state_speaking`
- `state_doa`
- `state_spinner`
- `state_dual_spinner`
- `state_pulse_wave`
- `state_custom_doa`

### Events

- `event_success`
- `event_warning`
- `event_error`
- `event_notification`
- `event_connected`
- `event_disconnected`
- `event_ack`
- `event_timer_10s`
- `event_timer_30s`
- `event_timer_60s`

### System

- `system_boot`
- `system_shutdown`

## Wo geht es weiter?

- [Eigene Anzeigen Schritt fuer Schritt](effects_engine_tutorial.md)
- [Farben, Typen und Namen zum Nachschlagen](reference.md)
- [CLI und API](api_guide.md)
- [Entwickler-Doku zur Effects Engine](dev/effects_engine_dev.md)
