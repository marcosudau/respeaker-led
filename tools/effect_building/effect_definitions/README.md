# effects

Hier liegen die Python-Buildquellen fuer das separate Effekt-Building unter `tools/effect_building/`.

Jede Python-Datei in diesem Ordner kann eine oder mehrere Effektdefinitionen fuer den Generator enthalten.

Wichtig:

- Der laufende Service scannt diesen Ordner nicht direkt.
- Der Service arbeitet mit gebauten `.lefx`- und `.lefxset`-Artefakten.
- Das normale EXE-/Release-Building unter `build-tools/` konsumiert diese Artefakte nur.

Mehr dazu:

- `docs/effects.md`
- `docs/current_approach.md`
- `tools/effect_building/BUILD_PROCESS.md`
