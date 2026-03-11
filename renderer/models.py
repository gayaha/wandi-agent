"""Pydantic v2 data models for the renderer integration layer."""

import re
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


ALLOWED_FONTS = {"Heebo", "Assistant", "Rubik", "Frank Ruhl Libre"}


class BrandConfig(BaseModel):
    """Per-client brand configuration for Remotion video rendering.

    All fields are optional with defaults that match the current hardcoded look.
    Hex color values are validated and normalized to uppercase.
    font_family is restricted to the curated set of loaded fonts.
    """

    primary_color: str = "#FFFFFF"
    secondary_color: str = "#FFFFFF"
    font_family: str = "Heebo"
    hook_font_size: int = Field(default=52, ge=20, le=120)
    body_font_size: int = Field(default=36, ge=14, le=80)
    overlay_color: str = "#000000"
    overlay_opacity: float = Field(default=0.55, ge=0.3, le=0.8)
    border_radius: int = Field(default=16, ge=0, le=100)
    text_position: Literal["top", "center", "bottom"] = "top"
    text_align: Literal["center", "right", "left"] = "center"
    animation_style: str | None = None

    @field_validator("primary_color", "secondary_color", "overlay_color", mode="before")
    @classmethod
    def validate_hex_color(cls, v: Any) -> str:
        """Validate hex color and normalize to uppercase."""
        if not isinstance(v, str):
            raise ValueError(f"Color must be a string, got {type(v)}")
        if not re.match(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$", v):
            raise ValueError(
                f"Invalid hex color '{v}'. Expected format: #RGB or #RRGGBB"
            )
        return v.upper()

    @field_validator("font_family", mode="before")
    @classmethod
    def validate_font_family(cls, v: Any) -> str:
        """Validate font family against the curated allowed set."""
        if v not in ALLOWED_FONTS:
            raise ValueError(
                f"Font family '{v}' is not in the curated set. "
                f"Allowed: {sorted(ALLOWED_FONTS)}"
            )
        return v


class RenderRequest(BaseModel):
    """Request payload for submitting a video render job."""

    source_video_url: str
    hook_text: str
    body_text: str
    record_id: str
    text_direction: Literal["rtl", "ltr"] = "rtl"
    animation_style: Literal["fade", "slide"] = "fade"
    duration_in_seconds: int = Field(default=15, ge=3, le=90)
    callback_url: str | None = None
    client_id: str | None = None
    awareness_stage: int | None = Field(default=None, ge=1, le=5)
    brand_config: BrandConfig | None = None


class JobStatus(BaseModel):
    """Status of a render job returned by the renderer service."""

    state: Literal[
        "accepted",
        "rendering",
        "downloading",
        "uploading",
        "completed",
        "failed",
        "timed_out",
    ]
    progress: float = 0.0
    video_url: str | None = None
    error: str | None = None
