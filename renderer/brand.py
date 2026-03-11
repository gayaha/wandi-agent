"""Brand configuration module — SDMF stage modifiers and brand resolution."""

from typing import Any

from renderer.models import BrandConfig


# SDMF awareness stage modifiers.
# Each stage adjusts visual emphasis relative to the brand's base config.
# Stage 1 = highest urgency/emotion (large hook, bold weight)
# Stage 3 = default authority tone
# Stage 5 = lowest urgency (rational/comparison)
STAGE_MODIFIERS: dict[int, dict[str, Any]] = {
    1: {"hook_size_scale": 1.15, "hook_font_weight": 900, "animation_speed_ms": 400},
    2: {"hook_size_scale": 1.10, "hook_font_weight": 700, "animation_speed_ms": 400},
    3: {"hook_size_scale": 1.00, "hook_font_weight": 700, "animation_speed_ms": 500},
    4: {"hook_size_scale": 0.95, "hook_font_weight": 600, "animation_speed_ms": 600},
    5: {"hook_size_scale": 0.95, "hook_font_weight": 600, "animation_speed_ms": 600},
}

# Default stage when awareness_stage is not provided
_DEFAULT_STAGE = 3


def resolve_brand_for_render(
    brand: BrandConfig, awareness_stage: int | None
) -> dict[str, Any]:
    """Merge brand base config with SDMF stage modifiers.

    Returns a camelCase dict suitable for inclusion in the Remotion payload.

    Args:
        brand: The client's BrandConfig (or defaults if no client).
        awareness_stage: SDMF stage 1-5. Uses stage 3 (default) when None.

    Returns:
        dict with all brand fields in camelCase for Remotion's BrandConfigSchema.
    """
    stage = awareness_stage if awareness_stage is not None else _DEFAULT_STAGE
    modifiers = STAGE_MODIFIERS.get(stage, STAGE_MODIFIERS[_DEFAULT_STAGE])

    hook_font_size = round(brand.hook_font_size * modifiers["hook_size_scale"])

    return {
        "primaryColor": brand.primary_color,
        "secondaryColor": brand.secondary_color,
        "fontFamily": brand.font_family,
        "hookFontSize": hook_font_size,
        "bodyFontSize": brand.body_font_size,
        "hookFontWeight": modifiers["hook_font_weight"],
        "overlayColor": brand.overlay_color,
        "overlayOpacity": brand.overlay_opacity,
        "borderRadius": brand.border_radius,
        "textPosition": brand.text_position,
        "textAlign": brand.text_align,
        "animationSpeedMs": modifiers["animation_speed_ms"],
    }
