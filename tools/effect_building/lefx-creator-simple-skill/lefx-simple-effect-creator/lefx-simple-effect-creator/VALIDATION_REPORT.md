# Validierungsbericht der mitgelieferten Beispiele

Die vier Beispielquellen wurden gegen den im bereitgestellten Projektstand
enthaltenen LEFX-V2-Packager geprüft.

## Ausgeführt

Für jede Quelle:

```powershell
python .\tools\effect_packager.py validate-effect-source <quelle>
python .\tools\effect_packager.py pack-effect <quelle> <ausgabe.lefx>
python .\tools\effect_packager.py verify-effect-package <ausgabe.lefx>
```

Zusätzlich wurden Renderaufrufe zu mehreren Zeitpunkten mit `led_count=12`
und `led_count=5` ausgeführt.

## Ergebnis

| Beispiel | Quellenvalidierung | Paketbau | Paketverifikation | Renderprüfung |
|---|---|---|---|---|
| `state_soft_pulse` | erfolgreich | erfolgreich | erfolgreich | erfolgreich |
| `state_rotating_segment` | erfolgreich | erfolgreich | erfolgreich | erfolgreich |
| `timed_overlay_sweep` | erfolgreich | erfolgreich | erfolgreich | erfolgreich |
| `event_short_pulse` | erfolgreich | erfolgreich | erfolgreich | erfolgreich |

Die Buildartefakte sind nicht Bestandteil des Skills. Der Skill enthält nur
die bearbeitbaren Beispielquellen.
