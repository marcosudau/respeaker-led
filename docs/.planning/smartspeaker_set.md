# SmartSpeaker-Set

## Status

Das kuratierte SmartSpeaker-Set ist bewusst noch nicht in `main` integriert.
Der aktuelle Hauptstand liefert die technisch bereinigte, vollstaendige
Standardbibliothek `default-effects`, aber noch kein als Produktpaket
freigegebenes SmartSpeaker-Set.

Die bisherige Arbeitsauswahl verbleibt im separaten Experiment, bis die
Effekte am echten Geraet bewertet und gestalterisch abgestimmt wurden. In
`main` liegen daher noch keine SmartSpeaker-Setdefinition, kein spezielles
Build-Skript und kein gebautes `smartspeaker-set.lefxset`.

## Naechste Schritte

1. geeignete States, Overlays und Events aus der Standardbibliothek auswaehlen
2. Varianten am ReSpeaker vergleichen, doppelte Muster entfernen und Parameter abstimmen
3. hochwertige Presets und nachvollziehbare Rollen festlegen
4. das Ergebnis als separates LEFXSET bauen, validieren und erst danach nach `main` uebernehmen

Das LED Effect Studio unter `tools/PySide6TestApp/` unterstuetzt diese spaetere
Kuration bereits mit dynamischen Parametern, JSON-Entwuerfen sowie Filtern nach
Paketquellen und optionalen lokalen Setauswahlen.
