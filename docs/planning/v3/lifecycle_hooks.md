# V3-Idee: optionale Lifecycle-Hooks

Status: Ideensammlung, nicht Teil von LEFX V2 und keine Umsetzungsfreigabe.

## Ausgangspunkt

V2 ist absichtlich renderorientiert. `BaseEffect` besitzt `render()` und fuer
Pull-Overlays optional `sample_inputs()`. Start, Stop, Reset, Update und
Finished-Signale existieren nicht. Endliche Lebensdauer bleibt Eigentum der
Engine.

## Denkbare V3-Erweiterung

Fuer Effekte, die echten internen Zustand benoetigen, koennte eine spaetere
SDK-Version optionale Hooks anbieten:

```python
def on_start(self, ctx: StartContext) -> None: ...
def update(self, ctx: UpdateContext, delta_seconds: float) -> None: ...
def on_stop(self, ctx: StopContext, reason: StopReason) -> None: ...
```

Offene Architekturfragen:

- Ist Zustand pro Instanz garantiert oder wird eine Effektklasse geteilt?
- Wie werden Neustart, Persistenz und Wiederherstellung definiert?
- Wie bleiben Renderresultate bei wechselnder FPS deterministisch?
- Darf ein Hook I/O ausfuehren oder muss das weiterhin in Integrationen liegen?
- Welche Zeit- und Fehlerbudgets gelten?
- Wie werden alte V2-Pakete unveraendert weiter unterstuetzt?
- Braucht V3 wirklich ein Paket-seitiges Endsignal, oder bleibt Dauer immer
  engine-gesteuert?

## Leitplanke

Hooks sollten nur eingefuehrt werden, wenn reale Effekte mit dem
zeitabgeleiteten V2-Modell nicht sauber darstellbar sind. Sie duerfen nicht zu
einer zweiten, paketgesteuerten Lifecycle-Engine fuehren.
