"""Pydantic v2 data models for the renderer integration layer."""

import re
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


ALLOWED_FONTS = {"Heebo", "Assistant", "Rubik", "Frank Ruhl Libre"}


class TextSegment(BaseModel):
    """A timed text segment for multi-segment Reel rendering.

    Each segment has a role (hook/body/cta), timing (start/end in seconds),
    and optional per-segment animation style override.
    """

    text: str
    start_seconds: float = Field(ge=0.0)
    end_seconds: float
    animation_style: Literal["fade", "slide"] = "fade"
    role: Literal["hook", "body", "cta"]

    @model_validator(mode="after")
    def validate_timing(self) -> "TextSegment":
        """Ensure end_seconds is strictly greater than start_seconds."""
        if self.end_seconds <= self.start_seconds:
            raise ValueError(
                f"end_seconds ({self.end_seconds}) must be greater than "
                f"start_seconds ({self.start_seconds})"
            )
        return self


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
    """Request payload for submitting a video render job.

    Supports two input modes:
    1. Segments mode: provide ``segments`` array (1-5 TextSegment items)
    2. Legacy mode: provide both ``hook_text`` and ``body_text``

    Both modes may be provided simultaneously; segments take priority in the
    rendering pipeline. Providing neither raises a validation error.
    """

    source_video_url: str
    hook_text: str | None = None
    body_text: str | None = None
    record_id: str
    text_direction: Literal["rtl", "ltr"] = "rtl"
    animation_style: Literal["fade", "slide"] = "fade"
    duration_in_seconds: int | None = Field(default=None, ge=3, le=600)
    callback_url: str | None = None
    client_id: str | None = None
    awareness_stage: int | None = Field(default=None, ge=1, le=5)
    brand_config: BrandConfig | None = None
    segments: list[TextSegment] | None = None

    @model_validator(mode="after")
    def validate_content_source(self) -> "RenderRequest":
        """Validate that content is provided via segments or legacy hook/body text.

        When segments is provided, enforces:
        - count 1-5
        - no overlap (each segment starts at or after the previous one ends)
        - all segments end within duration_in_seconds

        When segments is not provided:
        - both hook_text and body_text must be present
        """
        has_segments = self.segments is not None
        has_legacy = self.hook_text is not None and self.body_text is not None

        if not has_segments and not has_legacy:
            raise ValueError(
                "Provide either 'segments' (list of TextSegment) or both "
                "'hook_text' and 'body_text'"
            )

        if has_segments:
            segs = self.segments
            if len(segs) < 1 or len(segs) > 5:
                raise ValueError(
                    f"segments must contain 1-5 items, got {len(segs)}"
                )
            for i in range(1, len(segs)):
                if segs[i].start_seconds < segs[i - 1].end_seconds:
                    raise ValueError(
                        f"Segment {i} (start={segs[i].start_seconds}) overlaps "
                        f"with segment {i - 1} (end={segs[i - 1].end_seconds})"
                    )
            # Only check segment bounds when explicit duration is set.
            # When duration is None, Remotion will detect the actual video
            # duration via ffprobe and rescale segments accordingly.
            if self.duration_in_seconds is not None:
                for i, seg in enumerate(segs):
                    if seg.end_seconds > self.duration_in_seconds:
                        raise ValueError(
                            f"Segment {i} end_seconds ({seg.end_seconds}) exceeds "
                            f"duration_in_seconds ({self.duration_in_seconds})"
                        )

        return self


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
