# Tutorial: DoA-Push-Overlay

Das fertige Paket liegt unter
`docs/effect_examples/overlays/example_doa`. Es visualisiert einen extern
gelieferten Richtungswinkel, ohne die ReSpeaker-Hardware selbst anzusprechen.

## 1. Systemgrenze

Die ReSpeaker-Firmware kann DoA-Werte inzwischen unabhaengig vom internen
LED-Effekt liefern. Die Verantwortungen bleiben trotzdem getrennt:

1. Eine Integration liest den aktuellen Hardwarewert.
2. Sie setzt oder aktualisiert einen Overlay-Channel mit `direction_deg`.
3. Die Engine validiert den Input und verwaltet sein Lebenszeichen.
4. Das LEFX-Paket bildet den kanonischen Winkel auf den LED-Ring ab.

USB-, Treiber- und Wiederverbindungslogik gehoeren nicht in `effect.py`.

## 2. Datenvertrag

`color`, `brightness` und `width` sind stabile Konfiguration. Der veraenderliche
Messwert steht separat in `runtime_input_schema`:

```python
"direction_deg": EffectParamDefinition(
    name="direction_deg",
    type="angle_deg",
    required=False,
    nullable=True,
    aliases=("direction",),
)
```

Das Overlay ist `CONTROLLED`, transparent und verwendet
`InputSamplingPolicy(mode=InputMode.PUSH)`. Der Standard erlaubt drei
verpasste Heartbeats von je einer Sekunde. Waehrend der Karenzzeit bleibt der
letzte Wert wirksam; danach erhaelt der Renderer `None`.

## 3. Winkel abbilden

```python
center = round(
    (float(direction) % 360.0) / 360.0 * ctx.led_count
) % ctx.led_count
```

`0` und `360` zeigen auf dieselbe LED. Die Berechnung funktioniert fuer jede
Ringgroesse. Bei `None` gibt das Beispiel einen vollstaendig transparenten
Frame zurueck. Unbeteiligte LEDs bleiben ebenfalls `None`.

## 4. Ausloesen

Nachdem das Paket testweise geladen wurde:

```powershell
python .\main.py set overlay example_doa_overlay `
  --channel tutorial-doa --inputs '{"direction_deg":45}'
python .\main.py update overlay tutorial-doa `
  --inputs '{"direction_deg":180}'
python .\main.py update overlay tutorial-doa --inputs '{}'
python .\main.py clear overlay tutorial-doa
```

Das leere Update ist nur ein Lebenszeichen. Es behaelt den letzten gueltigen
Wert. Glattung ist bewusst nicht Bestandteil dieses Einstiegsbeispiels.

## 5. Fehlerfaelle

- Unbekannte Input-Namen werden abgewiesen.
- Ungueltige Winkel erreichen den Renderer nicht.
- `None` ergibt eine neutrale, transparente Anzeige.
- Ein ausbleibendes Lebenszeichen fuehrt nach der Karenzzeit zu `failed`.
- Das Schliessen des Channels beendet die Instanz unabhaengig vom Messwert.
