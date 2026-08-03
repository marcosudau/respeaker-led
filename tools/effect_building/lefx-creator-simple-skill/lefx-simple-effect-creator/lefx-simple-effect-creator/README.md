# LEFX Creator Simple

Dieser Skill ist für Agents gedacht, die normale LEFX-Effekte (V2) zuverlässig
erstellen sollen – auch mit einem kleineren Modell.

## Schwerpunkt

- States
- zeitgesteuerte Overlays
- Events
- Beispiele: Pulsieren, Rotieren, Blinken, Segmente, Sweeps, kurze Signale und Ähnliche...

Der Skill führt den Agenten von der Typentscheidung über die drei Quelldateien
bis zu Validierung, Paketbau und gezielten Renderprüfungen.

## Verwendung

Lege den gesamten Ordner dort ab, wo dein Agent Skills lädt. Eine mögliche
Aufgabe lautet:

```text
Nutze den Skill lefx-simple-effect-creator und erstelle einen dauerhaft
rotierenden State mit einem vier LEDs breiten Segment, weichem Schweif,
konfigurierbarer Farbe, Helligkeit, Geschwindigkeit und Drehrichtung.
Validiere und baue die Quelle anschließend.
```

Die normativen Regeln bleiben in der Projektdokumentation unter
`docs/effect-system/`. Der Skill verdichtet sie zu einem festen Arbeitsablauf.
