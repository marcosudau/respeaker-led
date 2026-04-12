
## Effect-Building
- Lass uns im nächsten Schritt das Effect-Building weiter spezifizieren.
- Bitte erstelle eine Folge-md-Datei, in der du ein Konzept zu folgenden Ideen vorstellst... 
- Erstmal ohne tatsächliche Änderungen durchzuführen.
- Gerne auch mit deiner Meinung/ Einschätzung und ggfs Änderungs- oder Verbesserungsvorschlägen...

### single-effect (*.lefx)
- Tool, zum erstellen von einzelnen \*.lefx-Dateien 
- Ordner, effect.py und effect.yaml werden automatisch erstellt
- Angabe von Assets / Py-Dateien wird unterstützt für zusätzliche Logik
- Unterstützt die Definition von Effekten durch ausgefüllte yaml/json 
- Kommentiertes yaml/json-Template wird als Vorlage erstellt.
- In einer json können mehrere Effekte hintereinander definiert werden-> jeweils eine eigene \*.lefx-Datei
- Validiert, dass alle benötigten Angaben vorhanden und schlüssig sind.

### effect-set (*.lefxset)
- Tool, das mehrere \*.lefx-Dateien in eine \*.lefxset-Datei zusammenpackt
- Zwischenschritt über einzelne \*.lefx-Dateien immer erforderlich...
- source-id muss übereinstimmen... sonst wird Datei übersprungen und nicht mit aufgenommen

