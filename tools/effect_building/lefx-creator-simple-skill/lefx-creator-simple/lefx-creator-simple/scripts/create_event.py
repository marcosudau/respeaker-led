from __future__ import annotations

from pathlib import Path
from textwrap import dedent


EFFECT_YAML = dedent(
    """
    # Diese Datei wurde von scripts/create_event.py erzeugt.
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
    #
    # Siehe SKILL.md, Abschnitt 9 "Defaults und Presets".

    presets:
      <PRESET_ID>:
        title: "<PRESET_TITLE>"
        description: "<PRESET_DESCRIPTION>"
        params:
          duration_ms: 1000
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
        QueueMode,
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

            # Durch create_event.py bereits festgelegt.
            definition_type=DefinitionType.EVENT,

            # duration_ms ist fuer Events verpflichtend und deshalb bereits
            # aktiv vorhanden. Default und Grenzen an den konkreten Effekt
            # anpassen. Weitere Parameter gemaess Abschnitt 4 und 5 ergaenzen.
            parameter_schema={
                "duration_ms": EffectParamDefinition(
                    name="duration_ms",
                    type="duration_ms",
                    default=1000,
                    minimum=1,
                    unit="ms",
                ),
                <ADDITIONAL_PARAMETER_SCHEMA>
            },
            defaults={
                "duration_ms": 1000,
                <ADDITIONAL_DEFAULT_VALUES>
            },

            # REQUIRED - siehe Abschnitt 2C und Abschnitt 6.
            capabilities=EffectCapabilities(
                playback_modes=(PlaybackMode.SINGLE_RUN,),
                supports_transparency=<SUPPORTS_TRANSPARENCY>,
                supports_duration_override=<SUPPORTS_DURATION_OVERRIDE>,
                supports_queueing=True,
            ),
            layer_rules={
                LayerId.EVENT_LAYER: LayerRule(
                    allowed=True,
                    allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
                    requires_finite_duration=True,
                    allows_transparency=<SUPPORTS_TRANSPARENCY>,
                    queue_mode=QueueMode.PRIORITY_FIFO,
                )
            },

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
            # - den endlichen Ablauf aus Startzeit und Dauer berechnen.
            # - bei transparenter Komposition unbeteiligte LEDs als None lassen.
            # - keine eigenen Timer, Threads oder Framezaehler verwenden.
            #
            # Entferne die folgende Abbruchzeile erst, wenn die konkrete
            # Effektlogik vollstaendig implementiert wurde.
            del params
            raise NotImplementedError("<IMPLEMENT_EVENT_RENDER_LOGIC>")
    '''
).lstrip()


def request_target_directory() -> Path:
    raw = input("Zielordner fuer die neue Event-Effektquelle: ").strip()
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

    print(f"Event-Scaffold erstellt: {target}")
    print("Erzeugt: effect.yaml, effect.py, presets.yaml")
    print("Naechster Schritt: SKILL.md ab Abschnitt 2C durcharbeiten.")


if __name__ == "__main__":
    main()
