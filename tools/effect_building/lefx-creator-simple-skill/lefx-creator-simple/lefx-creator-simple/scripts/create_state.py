from __future__ import annotations

from pathlib import Path
from textwrap import dedent


EFFECT_YAML = dedent(
    """
    # Diese Datei wurde von scripts/create_state.py erzeugt.
    # Die Platzhalter muessen vor Build und Validierung ersetzt werden.

    package_id: <PACKAGE_ID>
    source_id: <SOURCE_ID>
    entry_class: <CLASS_NAME>
    min_service_version: 1.0.0
    """
).lstrip()


PRESETS_YAML = dedent(
    """
    # Presets konfigurieren diese Definition. Sie duerfen Typ, Layer und
    # Lebenszyklus nicht veraendern.
    #
    # REQUIRED:
    # - Alle Platzhalter ersetzen.
    # - Nur Parameter eintragen, die in effect.py unter parameter_schema
    #   deklariert wurden.
    # - Keine Runtime-Werte in Presets eintragen.
    #
    # Siehe SKILL.md, Abschnitt 9 "Defaults und Presets".

    presets:
      <PRESET_ID>:
        title: "<PRESET_TITLE>"
        description: "<PRESET_DESCRIPTION>"
        params:
          <PRESET_PARAMETERS>
        tags:
          - <TAG>
    """
).lstrip()


EFFECT_PY = dedent(
    '''
    from __future__ import annotations

    from respeaker_led.core.effect_schema import (
        BaseEffect,
        ColorModel,
        CompositionMode,
        DefinitionType,
        EffectCapabilities,
        EffectDefinition,
        EffectParamDefinition,
        LayerId,
        LayerRule,
        PlaybackMode,
        RenderContext,
    )


    # Dieses Scaffold ist absichtlich noch nicht ausfuehrbar.
    # Arbeite die Entscheidungen in SKILL.md der Reihe nach ab und ersetze
    # danach jeden Platzhalter in spitzen Klammern.


    class <CLASS_NAME>(BaseEffect):
        definition = EffectDefinition(
            # REQUIRED - siehe SKILL.md, Abschnitt 8 "IDs und Metadaten".
            id="<EFFECT_ID>",
            title="<EFFECT_TITLE>",
            description="<EFFECT_DESCRIPTION>",

            # Durch create_state.py bereits festgelegt.
            definition_type=DefinitionType.STATE,

            # REQUIRED - siehe SKILL.md:
            # - Abschnitt 4 "Farbmodell"
            # - Abschnitt 5 "Parameter"
            parameter_schema={
                <PARAMETER_SCHEMA>
            },
            defaults={
                <DEFAULT_VALUES>
            },

            # REQUIRED - Ergebnis aus Abschnitt 2A und Abschnitt 6 eintragen.
            # Den vollstaendigen capabilities/layer_rules-Block aus Abschnitt 6.1
            # an dieser Stelle einsetzen.
            <STATE_CAPABILITIES_AND_LAYER_RULES>

            # REQUIRED - siehe Abschnitt 4 und Abschnitt 3.
            color_model=<COLOR_MODEL>,
            composition=<COMPOSITION_MODE>,
            animated=<ANIMATED>,
            directional=<DIRECTIONAL>,

            # REQUIRED - kurze, passende Katalogbegriffe einsetzen.
            tags=(<TAGS>),
        )

        def render(self, ctx: RenderContext) -> list[int | None]:
            params = {**ctx.definition.defaults, **ctx.params}

            # REQUIRED - siehe SKILL.md:
            # - Abschnitt 7 "Renderlogik"
            # - Abschnitt 7.4 "Visuelle Grundmuster"
            #
            # Verbindlich:
            # - ctx.led_count verwenden, niemals 12 fest codieren.
            # - exakt ctx.led_count Werte zurueckgeben.
            # - zeitliche Bewegung aus Enginezeit berechnen.
            # - nur deklarierte und bereits validierte Parameter verwenden.
            # - keine eigenen Timer, Threads oder Framezaehler verwenden.
            #
            # Entferne die folgende Abbruchzeile erst, wenn die konkrete
            # Effektlogik vollstaendig implementiert wurde.
            del params
            raise NotImplementedError("<IMPLEMENT_STATE_RENDER_LOGIC>")
    '''
).lstrip()


def request_target_directory() -> Path:
    raw = input("Zielordner fuer die neue State-Effektquelle: ").strip()
    if not raw:
        raise SystemExit("Abbruch: Es wurde kein Zielordner angegeben.")

    target = Path(raw).expanduser().resolve()
    if target.exists():
        raise SystemExit(f"Abbruch: Der Zielordner existiert bereits: {target}")
    return target


def write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> None:
    target = request_target_directory()
    try:
        target.mkdir(parents=True, exist_ok=False)
        write_file(target / "effect.yaml", EFFECT_YAML)
        write_file(target / "effect.py", EFFECT_PY)
        write_file(target / "presets.yaml", PRESETS_YAML)
    except Exception:
        if target.exists():
            for file_name in ("effect.yaml", "effect.py", "presets.yaml"):
                candidate = target / file_name
                if candidate.exists():
                    candidate.unlink()
            try:
                target.rmdir()
            except OSError:
                pass
        raise

    print(f"State-Scaffold erstellt: {target}")
    print("Erzeugt: effect.yaml, effect.py, presets.yaml")
    print("Naechster Schritt: SKILL.md ab Abschnitt 2A durcharbeiten.")


if __name__ == "__main__":
    main()
