from __future__ import annotations

from src.core.effect_schema import BaseEffect, EffectCapabilities, EffectDefinition, PlaybackMode, RenderContext
from src.engine.renderer import render_visual_to_pixels

from .common import _compatibility_rules, _merge_params, _parse_visual


class LegacyVisualEffect(BaseEffect):
    definition = EffectDefinition(
        id="legacy_visual",
        title="Legacy Visual",
        description="Kompatibilitaetshueller fuer bestehende Visual-Objekte auf der neuen Invocation-Schicht.",
        defaults={},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN, PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            supports_transparency=True,
            supports_duration_override=True,
            supports_queueing=True,
            data_driven=True,
        ),
        layer_rules=_compatibility_rules(),
        tags=("builtin", "compatibility"),
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        visual = _parse_visual(_merge_params(ctx).get("visual"))
        if visual is None:
            return [None] * ctx.led_count
        return render_visual_to_pixels(visual, ctx.now)