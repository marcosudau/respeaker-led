# LEFX Simple Effect Creator

Dieser Skill führt Agents schrittweise durch die Erstellung normaler
LEFX-V2-States, Overlays und Events.

## Inhalt

```text
lefx-simple-effect-creator/
├── SKILL.md
├── README.md
└── scripts/
    ├── create_state.py
    ├── create_overlay.py
    └── create_event.py
```

Die drei Skripte sind vollständig eigenständig. Jedes Skript enthält die
Vorlagen für `effect.yaml`, `effect.py` und `presets.yaml` direkt im eigenen
Quelltext. Es gibt keine externen Template-Dateien und keine Kommandozeilen-
Flags.

Aufruf:

```powershell
python .\scripts\create_state.py
python .\scripts\create_overlay.py
python .\scripts\create_event.py
```

Nach dem Start fragt das gewählte Skript nur nach dem Zielordner. Die erzeugte
Quelle enthält absichtlich ungültige Pflichtplatzhalter und wird erst nach dem
vollständigen Durcharbeiten der `SKILL.md` ausführbar und validierbar.
