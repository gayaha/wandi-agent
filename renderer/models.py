"""Pydantic v2 data models for the renderer integration layer."""

from typing import Literal
from pydantic import BaseModel, Field


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
