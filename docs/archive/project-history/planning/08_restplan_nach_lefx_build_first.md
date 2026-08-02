# Restplan nach LEFX Build First

Hinweis:

Dieses Dokument ist ein historischer Zwischenplan vor der spaeteren Bereinigung der finalen Build- und Runtime-Pfade.
Wenn hier alte Pfade oder noch offene Aufgaben genannt werden, sind sie nicht automatisch der heutige Ist-Zustand.
Fuer den aktuellen Stand sind `docs/current_approach.md`, `docs/effects.md` und `build-tools/README.md` massgeblich.

Diese Datei aktualisiert den Implementierungsplan nach dem abgeschlossenen Build-First-Meilenstein fuer die Standard-Effekte.

Historischer Hinweis:

Die hier genannten Publikationspfade unter `src/led_effects/...` beschreiben einen damaligen Zwischenstand.
Der heutige Ist-Zustand trennt Effekt-Building unter `tools/effect_building/` vom normalen Build unter `build-tools/`.

## Aktueller Stand

- Die Build-Strecke unter tools/effect_building erzeugt eigenstaendige .lefx-Pakete fuer alle Standard-Effekte.
- Daraus wird erfolgreich eine default-effects.lefxset gebaut.
- Das gebaute Set wurde in dieser Zwischenstufe noch ueber alte Publish-Pfade betrachtet; heute liegt die Publish-Kopie unter `tools/effect_building/build/published/default-effects.lefxset`.
- Der aktuelle Build-Stand umfasst 37 Effekte sowie jeweils 148 eingebettete Presets und Commands.

## Was damit bewusst noch nicht erledigt ist

- Die Runtime bootstrapped Standard-Effekte noch nicht primaer aus der default-effects.lefxset.
- Alte Built-in-Quellpfade und Discovery-Pfade sind noch im Runtime-Code vorhanden.
- Die finale Parametervereinheitlichung ist noch nicht ueberall abgeschlossen.
- Dokumentation und Release-Pfade sind erst teilweise auf das neue Artefaktmodell umgestellt.

## Reihenfolge fuer die verbleibenden Arbeiten

## Schritt 1: Runtime auf Artefakte umstellen

Ziel:

- Standard-Effekte werden beim Start aus der gebauten default-effects.lefxset geladen.
- Engine und Service lesen fertige Artefakte statt Python-Quellbibliotheken.

Arbeiten:

- build_default_effect_registry und verwandte Bootstrap-Pfade auf default-effects.lefxset ausrichten
- Paket- und Set-Suchpfade fuer Dev, Release und Bundle sauber festziehen
- Fallback-Verhalten fuer fehlende oder defekte Standard-Artefakte definieren

Testbar durch:

- Runtime- und Registry-Tests mit echter default-effects.lefxset
- Service-Start-Smoketests mit leerer und mit vorhandener Publish-Kopie

Abschlusskriterium:

- Der normale Dienststart benoetigt fuer Standard-Effekte keine direkte Modul-Discovery mehr.

## Schritt 2: Parameter und Normalisierung finalisieren

Ziel:

- Der finale Parametersatz ist ueber Runtime, CLI, API und Built-ins konsistent.

Arbeiten:

- base_color in Normalisierung, Runtime-Pfaden und oeffentlichen Nutzungsstellen durch background_color ersetzen
- max_brightness-Reste entfernen
- Standardparameter color, background_color, brightness, min_brightness, speed, direction, duration_ms ueberall konsistent behandeln
- Legacy-Normalisierung so anpassen, dass sie nur noch auf das finale Modell abbildet

Testbar durch:

- Normalisierungs- und Runtime-Tests
- API- und CLI-Regression fuer Effektaufrufe und Preset-Anwendungen

Abschlusskriterium:

- Es gibt fuer Standard-Effekte keine doppeldeutigen Altparameter mehr.

## Schritt 3: Registries und Metadatenpfade auf das Zielmodell schliessen

Ziel:

- EffectRegistry, EffectPresetRegistry und EffectCommandRegistry arbeiten vollstaendig auf dem finalen LEFX-Modell.

Arbeiten:

- verbleibende Sonderfaelle fuer Preset- und Command-Registrierung abbauen
- strukturierte Metadatenpfade in API und CLI auf das gebaute Standard-Set ausrichten
- Validierungsregeln fuer Command -> Preset -> Effect als primaeren Standard festziehen

Testbar durch:

- Registry- und API-Tests
- Client- und Service-Tests fuer Preset- und Command-Aufloesung

Abschlusskriterium:

- Effekt-, Preset- und Command-Metadaten kommen konsistent aus denselben Registries und Artefakten.

## Schritt 4: Altpfade und Uebergangslogik entfernen

Ziel:

- Uebergangslogik aus dem Build- und Runtime-Code wird bereinigt.

Arbeiten:

- Builder-Unterstuetzung fuer alte effect-presets-Quellen und Uebergangspfade entfernen, soweit nicht mehr benoetigt
- alte Built-in-Discovery-Helfer, Kompatibilitaetspfade und ueberholte Doppellogik abbauen
- pruefen, welche Dateien unter src/led_effects/effects kuenftig nur noch Build-Input sind und wie sie sauber abgegrenzt werden

Testbar durch:

- Architekturtests
- Paket- und Runtime-Regressionstests
- Build-Smoketests fuer LEFX und LEFXSET

Abschlusskriterium:

- Es bleibt nur noch ein offizieller Pfad fuer Build und Laufzeit uebrig.

## Schritt 5: Release, Bundle und Dokumentation nachziehen

Ziel:

- Deployment und Doku spiegeln das neue Artefaktmodell ohne Widersprueche wider.

Arbeiten:

- Release-Bundle, PyInstaller-Spec und Verifikationsskripte auf default-effects.lefxset ausrichten
- Doku zu Build, Laufzeit, Presets, Commands und Effektquellen konsolidieren
- veraltete Dokumente markieren, bereinigen oder entfernen
- neue Betriebs- und Fehlersuchdokumentation fuer das Artefaktmodell ergaenzen

Testbar durch:

- Release-Smokes
- Bundle-Verifikation
- manuelle Doku-Stichproben gegen den echten Build-Ablauf

Abschlusskriterium:

- Release-Artefakte enthalten die benoetigten Effektsets und die Doku beschreibt denselben Prozess, der im Repo ausgefuehrt wird.

## Empfohlene Abschlussreihenfolge

1. Runtime auf default-effects.lefxset umstellen
2. Parameter- und Normalisierungslage bereinigen
3. Registries und Metadatenpfade final schliessen
4. Altpfade entfernen
5. Release und Doku konsolidieren
