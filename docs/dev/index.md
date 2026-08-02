# Entwickler-Doku

Diese Seiten sind fuer interne Entwicklung gedacht.

Wenn du nur den Service starten und steuern willst, brauchst du diesen Bereich normalerweise nicht.

## Architektur und Orientierung

- [Aktuelle Architektur](architecture.md)
- [Build und Release](build.md)
- [Public Entry Points](public_entry_points.md)
- [CLI-Referenz](../cli_guide.md)
- [HTTP-API-Referenz](../api_guide.md)
- [LEFX-V2-Systemreferenz](../effect-system/README.md)
- [Effekte praktisch entwickeln](../effect-development/README.md)
- [Experiment-Workflow](experiment_workflow.md)

## Typische Dev-Fragen

### Ich will verstehen, wie States, Events und Overlays intern zusammenspielen

- [Layer und Komposition](../effect-system/03_layers_and_composition.md)
- [Typen und Lebenszyklen](../effect-system/04_effect_types_and_lifecycles.md)

### Ich will wissen, welche oeffentlichen Einstiegspunkte stabil sind

- [public_entry_points.md](public_entry_points.md)

### Ich will den aktuellen Service-Ansatz statt alter Migrationshistorie verstehen

- [architecture.md](architecture.md)

### Ich suche alte Planungs- oder Entwicklernotizen

- [Historisches Archiv](../archive/README.md)

### Ich will eine groessere oder hardwareabhaengige Aenderung ausprobieren

- [experiment_workflow.md](experiment_workflow.md)
