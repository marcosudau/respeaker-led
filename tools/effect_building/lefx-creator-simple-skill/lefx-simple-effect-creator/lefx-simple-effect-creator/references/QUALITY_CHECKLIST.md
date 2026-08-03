# Qualitäts- und Abschlusscheckliste

## Vor dem Schreiben

- [ ] Wunsch in einem Satz zusammengefasst.
- [ ] State, Timed Overlay oder Event eindeutig gewählt.
- [ ] Ähnliche vorhandene Definitionen und IDs gesucht.
- [ ] Nur wirklich notwendige Parameter festgelegt.
- [ ] Deckende oder transparente Komposition festgelegt.
- [ ] Passendes Beispiel aus diesem Skill gewählt.

## `effect.yaml`

- [ ] `package_id` korrekt.
- [ ] `source_id` korrekt.
- [ ] `entry_file` zeigt auf `effect.py` oder wird bewusst weggelassen.
- [ ] `entry_class` existiert exakt einmal lokal.
- [ ] Keine unbekannten Manifestfelder.

## `effect.py`

- [ ] Genau eine lokale `BaseEffect`-Unterklasse.
- [ ] ID, Titel und Beschreibung sind fachlich passend.
- [ ] Typ und gegebenenfalls `OverlayMode.TIMED` stimmen.
- [ ] `parameter_schema` enthält alle und nur die erlaubten Felder.
- [ ] `defaults` enthält keine unbekannten Felder.
- [ ] Farbmodell und Pflichtfelder stimmen.
- [ ] Farbige Definition deklariert `brightness` exakt `0.0..1.0`.
- [ ] `animated=True` besitzt `speed`.
- [ ] `directional=True` besitzt boolesches `reverse`.
- [ ] Endlicher Typ besitzt `duration_ms` oder `total_ms`.
- [ ] Layerregel und Playback-Modus passen zum Typ.
- [ ] Transparenz ist in Capability, Layerregel und Composition konsistent.
- [ ] `render()` verwendet absolute Zeitdifferenz.
- [ ] `render()` gibt exakt `ctx.led_count` Werte zurück.
- [ ] Kein fester Zwölf-LED-Frame.
- [ ] Keine fremden Effekt-, Controller- oder Serviceimporte.
- [ ] Keine Threads, Timer, Hooks oder Framezähler.

## `presets.yaml`

- [ ] Zwei bis vier sinnvolle Presets, sofern Varianten nützlich sind.
- [ ] Preset-IDs global eindeutig.
- [ ] Nur deklarierte Konfigurationsparameter.
- [ ] Keine Lebenszyklus- oder Typangaben.
- [ ] Klare Titel und Beschreibungen.

## Renderprüfungen

### Alle Effekte

- [ ] `led_count=12` liefert zwölf Einträge.
- [ ] Zusätzlich mindestens ein anderer positiver `led_count` geprüft.
- [ ] minimale Helligkeit geprüft.
- [ ] maximale Helligkeit geprüft.
- [ ] Ringumbruch geprüft, falls Positionen bewegt werden.
- [ ] `reverse=True` geprüft, falls vorhanden.

### State

- [ ] Startframe geprüft.
- [ ] späterer Frame geprüft.
- [ ] gleiche Zeit erzeugt denselben Frame.
- [ ] Wechsel der FPS verändert nicht die reale Bewegung.

### Timed Overlay und Event

- [ ] Anfang (`progress≈0`) geprüft.
- [ ] Mitte (`progress≈0.5`) geprüft.
- [ ] Ende (`progress≈1`) geprüft.
- [ ] Dauer-Override geprüft, falls unterstützt.

## Werkzeuge

```powershell
python .\tools\effect_packager.py validate-effect-source <quelle>
python .\tools\effect_packager.py pack-effect <quelle> <ausgabe.lefx>
python .\tools\effect_packager.py verify-effect-package <ausgabe.lefx>
```

## Abschlussbericht

- [ ] Dateien genannt.
- [ ] sichtbares Verhalten beschrieben.
- [ ] Parameter genannt.
- [ ] Presets genannt.
- [ ] tatsächlich ausgeführte Prüfungen genannt.
- [ ] keine erfundenen Testergebnisse.
