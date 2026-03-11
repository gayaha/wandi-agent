"""Renderer package — protocol, models, and implementations."""

from renderer.models import JobStatus, RenderRequest
from renderer.protocol import VideoRendererProtocol
from renderer.remotion import RemotionRenderer


def get_renderer() -> VideoRendererProtocol:
    """Factory that returns the default renderer implementation."""
    return RemotionRenderer()


__all__ = [
    "VideoRendererProtocol",
    "RenderRequest",
    "JobStatus",
    "RemotionRenderer",
    "get_renderer",
]
