##  Meine Anmerkungen zu "08_10_konzept_effekt_dateien.md"

Da Presets bisher zwar angelegt waren, effektiv doch nicht ein einziges Mal benutzt wurden, würde ich vorschlagen dass wir um Verwirrung zu vermeiden, das alte Konzept erstmal komplett abbauen bzw. rausnehmen... 
Also sowohl im Code als auch in der Docu es komplett und sauber entfernen. Dann brauchen wir auch nicht auf Abwärtskompatibilität zu achten.
Deine 3-Ebenen-Einteilung finde Ich super, also die Aufteilung in:
- dem parametrisierbaren Effekt
- dem benannten Preset
- dem festen Command

Ich würde es jedoch nicht in der lefxset-Datei festlegen, sondern bereits in der einzelnen lefx-Datei. So bleiben diese als einzelne Effekte unabhängig vom Set verwendbar, und ein Set bleibt weiterhin nur die Zusammenfassung von mehreren... 
Beispielsweise enthält die Datei dann den eigentlichen parametrisierbaren Effekt, für den darin einige presets mit den häufig verwendeten Einstellungen vorhanden sind.
Für die Presets könnten wir als Namenskonvention festlegen, dass sie beginnen mit "state_", "effect_", "overlay_" oder "event_"... Je nachdem auf welchen Layer sie festgelegt wurden...
die commands könnten dann ebenfalls in der lefx-Datei definiert werden und wie du vorgeschlagen hast als Trigger für die presets verwendet werden. 
Zusätzlich könnte man aber auch noch einige commands definieren, mit denen (entweder manuell oder für übersichtlichere list-abfragen) Standard-Informationen abgerufen werden können...
Als Beispiel für den Effekt "soft_pulsing_ring":
- "soft_pulsing_ring.title" -Zum Abrufen des Titels
- "soft_pulsing_ring.description" -Zum Abrufen der Beschreibung
- "soft_pulsing_ring.params" -Zum Abrufen einer Liste mit allen unterstützten Parametern
- "soft_pulsing_ring.presets" -Zum Abrufen einer Liste mit allen Presets, untergliedert nach "states", "effects", "overlays" und "events" (Evtl auch einzeln abrufbar über "soft_pulsing_ring.states", usw...)
- "soft_pulsing_ring.commands" -Zum Abrufen einer Liste mit allen Commands, 
- "soft_pulsing_ring.info" -Zum Abrufen einer übersicht mit allen zuvor genannten infos...
- "soft_pulsing_ring.set" -Zum setzen des Effekts mit freier Parameterangabe.. (Bei nicht gesetzten Fallback auf default-Werte)

Was hälst du von diesem Vorschlag???


##  Weitere Anmerkungen
Ich hätte noch eine andere Sache die mich stört...
In  ring_effects.py ist es sehr unsauber gelöst, dass der Parameter "brightness" für alle gilt... 
Das sollten wir irgendwie besser/ allgemeingültiger lösen... 
Es wäre auch sinnvoll, bei effekten mit einer Helligkeitsspanne ("min_brightness"/"max_brightness") für den Maximalwert auch einfach nur "brightness" zu benutzen, damit wir diesen in einer allgemeinen Lösung mit ansprechen...
Ebenso würde mir dazu einfallen, dass der Parameter "speed" für alle animierten Effekte gültig ist

- Ich möchte, dass wir das neue Gesamt-Konzept im nächsten Schritt festmachen, sodass es insgesamt rund und schlüssig ist und keine inkonsistenzen oder Behelfslösungen mehr aufweist. 
- Dabei auch keine Rücksicht mehr auf Abwärtskompatibilität... Wenn wir eine Lösung haben die in sich rund ist, müssen wir das alte darauf anziehen... Soviel ist es ja noch nicht, dass es sich lohnen würde dafür Sonderwege zu behalten...
- Ich möchte das jetzt schnellstmöglich zu einem guten Abschluss bekommen, um den Branch wieder in Main zu mergen.