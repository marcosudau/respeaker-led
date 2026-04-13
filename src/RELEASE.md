# Release Guide

Dieses Projekt verwendet GitVersion im Continuous Deployment Mode.

## Patch-Releases (automatisch)
- Jeder Commit auf `main` erzeugt automatisch eine neue Patch-Version.
- Beispiel: `1.4.12` → Commit → `1.4.13`
- Es wird **kein Release** erstellt.
- Die Datei `VERSION.yaml` wird automatisch aktualisiert.

## Minor-Releases (manuell)
1. Entscheide, welche neue Version du möchtest, z. B. `1.5.0`.
2. Erstelle einen Tag:
   ```
   git tag v1.5.0
   git push --tags
   ```
3. Der Release-Workflow startet automatisch:
   - Tests
   - Build
   - Release-Bundle
   - Changelog
   - GitHub Release

## Major-Releases
Funktionieren identisch wie Minor-Releases:
```
git tag v2.0.0
git push --tags
```

## Changelog
Der Changelog wird automatisch aus allen Commits seit dem letzten Release generiert.