# Tutorial: kurzes Puls-Event

Das fertige Paket liegt unter
`docs/effect_examples/events/example_short_pulse`. Es zeigt einen einzelnen
Helligkeitsverlauf auf der priorisierten Event-Ebene.

## 1. Endlicher Vertrag

Ein Event erlaubt nur `EVENT_LAYER` und `SINGLE_RUN`. Seine Layer-Regel
verlangt eine endliche Dauer; `duration_ms` ist daher Teil des Schemas.
`supports_queueing=True` und `PRIORITY_FIFO` erlauben die Event-Queue.

Events besitzen keine Runtime-Inputs und koennen nach dem Emit nicht
aktualisiert werden.

## 2. Fortschritt berechnen

```python
duration_ms = ctx.invocation.requested_duration_ms or int(params["duration_ms"])
elapsed_ms = max(0.0, (ctx.now - ctx.invocation.created_at) * 1000.0)
progress = min(1.0, elapsed_ms / max(1, duration_ms))
pulse_progress = min(1.0, progress * float(params["speed"]))
intensity = math.sin(math.pi * pulse_progress) * float(params["brightness"])
```

Der Sinus startet bei null, erreicht in der Mitte sein Maximum und endet bei
null. `requested_duration_ms` hat Vorrang vor dem Paketdefault, wenn ein
zulaessiger Override angefordert wurde.

## 3. Wer beendet das Event?

Nicht das Paket. Es rendert fuer den von der Engine angeforderten Zeitpunkt.
Die Engine entfernt die Instanz automatisch am Ende der Dauer und aktiviert
gegebenenfalls das naechste Queue-Element. Ein `finished`-Flag waere in V2 ein
zweiter, widerspruechlicher Lifecycle.

## 4. Pruefen

Teste Frames bei Fortschritt `0.0`, `0.5` und `1.0`, eine alternative Dauer,
die maximale Helligkeit und einen ungueltigen Dauerwert. Danach kann das
geladene Paket mit folgendem Befehl ausgeloest werden:

```powershell
python .\main.py emit event example_short_pulse_event `
  --config '{"color":"blue","duration_ms":"600ms"}'
```
