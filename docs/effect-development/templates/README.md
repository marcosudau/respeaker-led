# Gueltige Basistemplates

Alle Vorlagen sind echte, validierbare LEFX-V2-Quellen. Ihre neutralen IDs und
Werte werden ersetzt; `TODO` markiert die Anpassungsstellen. Die Verzeichnisse
liegen ausserhalb der Standardquellen und werden daher nicht automatisch
registriert.

## Auswahl

- `tpl_state_basic`: unbestimmter, deckender Grundzustand
- `tpl_overlay_push`: kontrolliertes Overlay mit externen Channel-Updates
- `tpl_overlay_pull`: kontrolliertes Overlay mit `sample_inputs()`
- `tpl_overlay_timed`: automatisch endende Einblendung
- `tpl_event_basic`: einmaliges, endliches Signal

## Checkliste vor der Validierung

- `effect.yaml`: `package_id`, `source_id` und `entry_class` sind korrekt.
- `definition.id` ist global eindeutig und entspricht `snake_case`.
- `definition_type` und bei Overlays `overlay_mode` sind eindeutig.
- Layer-Regel und Playback-Modus passen zum Typ.
- Endliche Typen deklarieren `duration_ms` oder `total_ms`.
- Kontrollierte Overlays deklarieren Inputs getrennt von Konfiguration.
- Farbmodell, `brightness`, `speed` und `reverse` folgen dem V2-Vertrag.
- `defaults` enthalten nur deklarierte Konfigurationsfelder.
- Transparente Renderer geben fuer unbeteiligte LEDs `None` zurueck.
- Die Quelle importiert keine Controller- oder andere Effektlogik.
- Preset-IDs sind global eindeutig und enthalten nur Konfiguration.

## Pruefen

```powershell
python .\tools\effect_packager.py validate-effect-source `
  .\docs\effect-development\templates\tpl_state_basic
```

Eine neue Quelle sollte bevorzugt mit `init-effect` erzeugt werden. Die
Templates zeigen den vollstaendigen Vertrag der jeweiligen Variante und sind
keine zweite Scaffold-Implementierung.
