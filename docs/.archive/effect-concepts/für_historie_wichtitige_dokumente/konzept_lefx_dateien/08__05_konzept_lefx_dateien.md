##  Meine Anmerkungen zu "08_04_konzept_effekt_dateien.md"

- Zu commands.json habe Ich noch Fragen...
  - So wie Ich es sehe, werden die Befehle nur dort benannt, aber das müsste doch in den  die Einzel-befehlen festgelegt sein, oder wie funktionieren die?
  - Ebenso wundert mich, dass dort parameter angegeben werden (color, duration) weil die Einzel-befehle doch eigentlich auf parameter festgelegt sind??
  - Vielleicht verstehe ich das auch nicht richtig, dann korrigiere mich, aber eigentlich müsste das doch pro einzelnen befehl fest sein...  

- Zur API:
  - Du hast zur Registrierung diese Routen "POST /api/v1/effect-sources/register-package" und "POST /api/v1/effect-sources/register-set" angegeben...
  - Könnte man nicht besser nur "POST /api/v1/effect-sources/register" machen um es nach aussen einfacher zu machen, und dann intern unterscheiden... z.B. anhand des Dateiformats?
  - Gleiches dann natürlich auch bei cli
- Auch bei deinem Beispielbefehlsaufruf (kopiere Ich dir nochmal, dmit du weisst welchen ich meine) wurde der Parameter "color" mit angegeben... Das sollte doch eigentlich unmöglich sein, da ein registrierter befehl eine feste farbe hat.. Einer der wichtigsten Gründe ist ja, das die Anwendungen nichts mehr mit parametern zu tun haben, sondern nurnoch mit den befehlen... Also müssten für den selben effekt in anderer farbe ein seperater befehl angelegt sein...
{
  "command_name": "listening",
  "source_id": "app.voice_assistant",
  "payload": {
    "color": "#55CCFF"
  },
  "replace_existing": true
}
- Bei dem Befehlsaufruf könnte man 
- Bei dem Befehlsaufruf könnte man "replace_existing" weglassen, weil es ohnehin immer true sein muss, sonst bräuchte man den Befehl garnicht aufrufen...Und wenn im einzelbefehl die parmeter ohnehin fest sind, braucht man auch payload nicht...
- Wie findest du die Idee, bei der Registrierung eigene API-Routen anzulegen für source und jeden command, z.B:
  - "POST /api/v1/commands/voice_assistant"
    - Auflistung aller Befehle, die zu dieser Quelle registriert sind.
  - "POST /api/v1/commands/voice_assistant/listening"
    - Wenn nicht gesetzt: Setzt den Effekt im Layer(on), Ansonsten: togglet zwischen on und off
  - "POST /api/v1/commands/voice_assistant/listening/on"
    - es wird sichergestellt, das der effekt unabhängig vom aktuellen status, auf "on" gesetzt wird
  - "POST /api/v1/commands/voice_assistant/listening/off"
    - es wird sichergestellt, das der effekt unabhängig vom aktuellen status, auf "off" gesetzt wird
- Dadurch könnte man die Route "POST /api/v1/effect-commands" ganz sparen, weil man es mit in "/api/v1/commands" hat
- Die Route "POST /api/v1/effect-sources" kann bleiben wie du sie vorgeschlagen hast...



## Zu deinen noffenen Fragen...
1. Die strikte Release-Pruefung ist erstmal unwichtig, lass uns die auf später irgendwann verschieben um uns erstmal darauf zu konzentrieren, eine funktionierende Grund-Version zu erstellen.
2. Ja, das vorgeschlagene Schema ist gut, das nehmen wird...
3. Nein, nicht persistent speichern.. Zumindest nicht über "effect_sources.json"... Wenn die Dateien in dem Autodiscovery-Ordner liegen sollen sie aber erkannt und geladen werden..
4. Es reicht zuerst nur pack, inspect und verify ... (auch wegen Fokus auf funktionierende Grund-Version)
5. Von Anfang an nur mit .lefx und .lefxset arbeiten...
