# Umbauplanung

Dieser Ordner sammelt die zentrale Planungs- und Zieldokumentation fuer die Neuausrichtung des `led_controller` hin zu einem dauerhaft laufenden Dienst mit einer einzigen Engine.

## Einstieg

- [01_zielarchitektur.md](01_zielarchitektur.md)
  Gesamtbild der Zielarchitektur mit Mermaid-Uebersichten
- [02_effektdefinition_und_registry.md](02_effektdefinition_und_registry.md)
  Vollstaendige Struktur einer `EffectDefinition`, Registry- und Discovery-Modell
- [03_umbauplan.md](03_umbauplan.md)
  Umbauphasen, Reihenfolge und Dokumentation des Vorgehens
- [04_entscheidungen.md](04_entscheidungen.md)
  Bisher festgezogene Architekturentscheidungen
- [05_technisches_zielschema.md](05_technisches_zielschema.md)
  Konkrete Zielstruktur fuer Enums, Basisklassen, Registry und Discovery
- [06_implementierungsplan.md](06_implementierungsplan.md)
  Konkrete, einzeln testbare Umsetzungsschritte fuer den Umbau
- [07_empirischer_planabgleich_01_bis_05.md](07_empirischer_planabgleich_01_bis_05.md)
  Ausfuehrlicher Soll/Ist-Abgleich der urspruenglichen Planungsdokumente 01 bis 05

## Zweck dieses Ordners

Dieser Ordner soll waehrend des Umbaus die zentrale Arbeitsgrundlage sein fuer:

- Zielbild
- Architekturentscheidungen
- Datenmodelle
- Registry-/Discovery-Konzept
- Migrationsreihenfolge
- Fortschrittsdokumentation

## Arbeitsregel fuer die weitere Planung

Wenn wir bei einer Strukturfrage eine Entscheidung festziehen, sollte sie zuerst in [04_entscheidungen.md](04_entscheidungen.md) landen und danach in die Detaildokumente eingearbeitet werden.
