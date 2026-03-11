"""Tests for BrandConfig model, stage modifiers, and Airtable brand extraction."""

import pytest
from pydantic import ValidationError

from renderer.models import BrandConfig, RenderRequest
from renderer.brand import resolve_brand_for_render, STAGE_MODIFIERS
import airtable_client as at


# ── BrandConfig defaults ───────────────────────────────────────────────────────


def test_brand_config_all_defaults():
    """BrandConfig() with no args produces all expected defaults."""
    cfg = BrandConfig()
    assert cfg.primary_color == "#FFFFFF"
    assert cfg.secondary_color == "#FFFFFF"
    assert cfg.font_family == "Heebo"
    assert cfg.hook_font_size == 52
    assert cfg.body_font_size == 36
    assert cfg.overlay_color == "#000000"
    assert cfg.overlay_opacity == 0.55
    assert cfg.border_radius == 16
    assert cfg.text_position == "top"
    assert cfg.text_align == "center"
    assert cfg.animation_style is None


# ── BrandConfig validation ────────────────────────────────────────────────────


def test_brand_config_invalid_primary_color():
    """BrandConfig(primary_color='invalid') raises ValidationError."""
    with pytest.raises(ValidationError):
        BrandConfig(primary_color="invalid")


def test_brand_config_invalid_font_family():
    """BrandConfig(font_family='Arial') raises ValidationError (not in curated set)."""
    with pytest.raises(ValidationError):
        BrandConfig(font_family="Arial")


def test_brand_config_normalizes_color_uppercase():
    """BrandConfig(primary_color='#FF0000') stores '#FF0000' (uppercase)."""
    cfg = BrandConfig(primary_color="#FF0000")
    assert cfg.primary_color == "#FF0000"


def test_brand_config_lowercase_color_normalized():
    """BrandConfig(primary_color='#ff0000') normalizes to '#FF0000' (uppercase)."""
    cfg = BrandConfig(primary_color="#ff0000")
    assert cfg.primary_color == "#FF0000"


def test_brand_config_3char_hex_valid():
    """BrandConfig(primary_color='#abc') is valid (3-char hex accepted)."""
    cfg = BrandConfig(primary_color="#abc")
    assert cfg.primary_color == "#ABC"


def test_brand_config_overlay_opacity_too_low():
    """BrandConfig(overlay_opacity=0.2) raises ValidationError (below 0.3 min)."""
    with pytest.raises(ValidationError):
        BrandConfig(overlay_opacity=0.2)


def test_brand_config_overlay_opacity_too_high():
    """BrandConfig(overlay_opacity=0.9) raises ValidationError (above 0.8 max)."""
    with pytest.raises(ValidationError):
        BrandConfig(overlay_opacity=0.9)


def test_brand_config_overlay_opacity_boundary_low():
    """BrandConfig(overlay_opacity=0.3) is valid at minimum boundary."""
    cfg = BrandConfig(overlay_opacity=0.3)
    assert cfg.overlay_opacity == 0.3


def test_brand_config_overlay_opacity_boundary_high():
    """BrandConfig(overlay_opacity=0.8) is valid at maximum boundary."""
    cfg = BrandConfig(overlay_opacity=0.8)
    assert cfg.overlay_opacity == 0.8


# ── RenderRequest extension ───────────────────────────────────────────────────


def test_render_request_with_client_id_and_stage():
    """RenderRequest accepts optional client_id and awareness_stage."""
    req = RenderRequest(
        source_video_url="https://example.com/video.mp4",
        hook_text="Hook",
        body_text="Body",
        record_id="recABC",
        client_id="recABC",
        awareness_stage=3,
    )
    assert req.client_id == "recABC"
    assert req.awareness_stage == 3


def test_render_request_backward_compat():
    """RenderRequest with no client_id or awareness_stage still works."""
    req = RenderRequest(
        source_video_url="https://example.com/video.mp4",
        hook_text="Hook",
        body_text="Body",
        record_id="recABC",
    )
    assert req.client_id is None
    assert req.awareness_stage is None


def test_render_request_brand_config_optional():
    """RenderRequest accepts optional brand_config field."""
    cfg = BrandConfig(primary_color="#FF0000")
    req = RenderRequest(
        source_video_url="https://example.com/video.mp4",
        hook_text="Hook",
        body_text="Body",
        record_id="recABC",
        brand_config=cfg,
    )
    assert req.brand_config is not None
    assert req.brand_config.primary_color == "#FF0000"


# ── extract_brand_config ──────────────────────────────────────────────────────


def test_extract_brand_config_valid_color():
    """extract_brand_config maps 'Brand Primary Color' to primary_color."""
    record = {"id": "rec1", "fields": {"Brand Primary Color": "#FF0000"}}
    result = at.extract_brand_config(record)
    assert result.primary_color == "#FF0000"
    # Other fields should be defaults
    assert result.font_family == "Heebo"


def test_extract_brand_config_empty_string_treated_as_absent():
    """extract_brand_config treats empty string as absent, returns default."""
    record = {"id": "rec1", "fields": {"Brand Primary Color": ""}}
    result = at.extract_brand_config(record)
    assert result.primary_color == "#FFFFFF"  # default


def test_extract_brand_config_invalid_color_falls_back_to_defaults():
    """extract_brand_config with invalid color falls back to all defaults."""
    record = {"id": "rec1", "fields": {"Brand Primary Color": "not-a-color"}}
    result = at.extract_brand_config(record)
    # Should fall back to default BrandConfig
    assert result.primary_color == "#FFFFFF"
    assert result.font_family == "Heebo"


def test_extract_brand_config_multiple_fields():
    """extract_brand_config maps multiple Airtable fields correctly."""
    record = {
        "id": "rec1",
        "fields": {
            "Brand Primary Color": "#FF0000",
            "Brand Font Family": "Rubik",
            "Brand Hook Font Size": 60,
            "Brand Overlay Opacity": 0.5,
        },
    }
    result = at.extract_brand_config(record)
    assert result.primary_color == "#FF0000"
    assert result.font_family == "Rubik"
    assert result.hook_font_size == 60
    assert result.overlay_opacity == 0.5


def test_extract_brand_config_empty_record():
    """extract_brand_config with empty fields returns all defaults."""
    record = {"id": "rec1", "fields": {}}
    result = at.extract_brand_config(record)
    assert isinstance(result, BrandConfig)
    assert result.primary_color == "#FFFFFF"


def test_extract_brand_config_none_values_skipped():
    """extract_brand_config skips None values from Airtable."""
    record = {"id": "rec1", "fields": {"Brand Primary Color": None}}
    result = at.extract_brand_config(record)
    assert result.primary_color == "#FFFFFF"  # default, None was skipped


# ── resolve_brand_for_render ─────────────────────────────────────────────────


def test_resolve_brand_default_stage_none():
    """resolve_brand_for_render(BrandConfig(), None) uses stage 3 as default."""
    result = resolve_brand_for_render(BrandConfig(), None)
    assert isinstance(result, dict)
    # Stage 3 defaults: scale=1.00, weight=700, speed=500ms
    assert result["hookFontWeight"] == 700
    assert result["animationSpeedMs"] == 500
    # hook font size = 52 * 1.00 = 52
    assert result["hookFontSize"] == 52


def test_resolve_brand_stage1_larger_hook():
    """Stage 1 produces larger hook font size than stage 3."""
    brand = BrandConfig(hook_font_size=60)
    result_stage1 = resolve_brand_for_render(brand, 1)
    result_stage3 = resolve_brand_for_render(brand, 3)
    assert result_stage1["hookFontSize"] > result_stage3["hookFontSize"]


def test_resolve_brand_stage1_hook_font_size():
    """resolve_brand_for_render(BrandConfig(hook_font_size=60), 1) returns hookFontSize=round(60*1.15)=69."""
    brand = BrandConfig(hook_font_size=60)
    result = resolve_brand_for_render(brand, 1)
    assert result["hookFontSize"] == round(60 * 1.15)  # 69
    assert result["hookFontWeight"] == 900


def test_resolve_brand_stage3_hook_font_size():
    """resolve_brand_for_render(BrandConfig(hook_font_size=60), 3) returns hookFontSize=60, hookFontWeight=700."""
    brand = BrandConfig(hook_font_size=60)
    result = resolve_brand_for_render(brand, 3)
    assert result["hookFontSize"] == 60
    assert result["hookFontWeight"] == 700


def test_resolve_brand_camelcase_output():
    """resolve_brand_for_render returns camelCase keys."""
    result = resolve_brand_for_render(BrandConfig(), 3)
    assert "primaryColor" in result
    assert "secondaryColor" in result
    assert "fontFamily" in result
    assert "hookFontSize" in result
    assert "bodyFontSize" in result
    assert "hookFontWeight" in result
    assert "overlayColor" in result
    assert "overlayOpacity" in result
    assert "borderRadius" in result
    assert "textPosition" in result
    assert "textAlign" in result
    assert "animationSpeedMs" in result


def test_resolve_brand_different_colors_produce_different_output():
    """Two different BrandConfigs with same stage produce different primaryColor."""
    brand_red = BrandConfig(primary_color="#FF0000")
    brand_blue = BrandConfig(primary_color="#0000FF")
    result_red = resolve_brand_for_render(brand_red, 3)
    result_blue = resolve_brand_for_render(brand_blue, 3)
    assert result_red["primaryColor"] != result_blue["primaryColor"]


def test_resolve_brand_same_config_different_stages():
    """Same BrandConfig with stage 1 vs stage 3 produce different hookFontSize."""
    brand = BrandConfig()
    result1 = resolve_brand_for_render(brand, 1)
    result3 = resolve_brand_for_render(brand, 3)
    assert result1["hookFontSize"] != result3["hookFontSize"]


def test_resolve_brand_values_correct():
    """resolve_brand_for_render outputs match brand config values."""
    brand = BrandConfig(primary_color="#FF0000", font_family="Rubik", body_font_size=40)
    result = resolve_brand_for_render(brand, 3)
    assert result["primaryColor"] == "#FF0000"
    assert result["fontFamily"] == "Rubik"
    assert result["bodyFontSize"] == 40


# ── STAGE_MODIFIERS constant ──────────────────────────────────────────────────


def test_stage_modifiers_all_5_stages():
    """STAGE_MODIFIERS has entries for stages 1-5."""
    for stage in range(1, 6):
        assert stage in STAGE_MODIFIERS


def test_stage_modifiers_stage1_values():
    """Stage 1 modifier has correct values."""
    mod = STAGE_MODIFIERS[1]
    assert mod["hook_size_scale"] == 1.15
    assert mod["hook_font_weight"] == 900
    assert mod["animation_speed_ms"] == 400


def test_stage_modifiers_stage3_values():
    """Stage 3 modifier (default/authority) has correct values."""
    mod = STAGE_MODIFIERS[3]
    assert mod["hook_size_scale"] == 1.00
    assert mod["hook_font_weight"] == 700
    assert mod["animation_speed_ms"] == 500
