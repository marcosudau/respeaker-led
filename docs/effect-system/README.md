# LEFX V2: das Effektsystem

Diese Dokumentation beschreibt den verbindlichen Ist-Zustand des
LEFX-V2-Systems. Sie erklaert, wie States, Overlays und Events aufgebaut,
ausgefuehrt, gesteuert und als Pakete verteilt werden.

## Einstieg nach Ziel

### Ich moechte das System verstehen

1. [Ueberblick und Grundidee](01_overview.md)
2. [Begriffe und Systemobjekte](02_vocabulary.md)
3. [Layer und Komposition](03_layers_and_composition.md)
4. [Typen und Lebenszyklen](04_effect_types_and_lifecycles.md)

### Ich brauche die technische Referenz

5. [Schema V2](05_schema_v2.md)
6. [Parameter und Werte](06_parameters_and_values.md)
7. [Runtime-Eingaben](07_runtime_inputs.md)
8. [Pakete, IDs und Konfiguration](08_packages_ids_and_configuration.md)

### Ich moechte das System bedienen oder erweitern

9. [CLI und HTTP API](09_control_interface.md)
10. [Validierung und Build](10_validation_and_build.md)
11. [Architekturgrenzen](11_architecture_boundaries.md)
12. [Status und Ausblick](12_status_and_outlook.md)

## Praktische Entwicklung

Die Schritt-fuer-Schritt-Anleitungen, validierbaren Templates und
Tutorial-Pakete liegen getrennt unter
[Effektentwicklung](../effect-development/README.md).

## Verbindlichkeit

- Dieser Ordner beschreibt ausschliesslich den aktuellen Ist-Zustand.
- `docs/planning/` enthaelt noch nicht umgesetzte Entscheidungen.
- `docs/archive/` enthaelt historische und nicht normative Unterlagen.
- Bei einem Widerspruch ist die aktuelle Implementierung zusammen mit dieser
  Referenz massgeblich; der Widerspruch muss anschliessend korrigiert werden.
