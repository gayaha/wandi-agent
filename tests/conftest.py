"""Shared pytest fixtures for the renderer test suite."""

from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio

from renderer import JobStatus, RenderRequest, VideoRendererProtocol


@pytest.fixture
def sample_render_request() -> RenderRequest:
    """Return a valid RenderRequest with typical test values."""
    return RenderRequest(
        source_video_url="https://example.com/source.mp4",
        hook_text="Test hook text",
        body_text="Test body content",
        record_id="recABC123",
    )


@pytest.fixture
def mock_renderer() -> VideoRendererProtocol:
    """Return a mock object satisfying VideoRendererProtocol for unit tests.

    All async methods are replaced with AsyncMock so they can be awaited
    and have their calls inspected.
    """

    class _MockRenderer:
        render = AsyncMock(return_value="mock-job-id-001")
        get_status = AsyncMock(
            return_value=JobStatus(state="completed", progress=1.0)
        )
        health_check = AsyncMock(return_value=True)
        download_file = AsyncMock(return_value=None)

    return _MockRenderer()


@pytest_asyncio.fixture
async def app_client():
    """Return an httpx.AsyncClient configured to call the FastAPI app in-process.

    Uses ASGITransport so no real HTTP socket is opened — all requests are
    routed through the ASGI interface directly. Suitable for testing all
    FastAPI routes without a running server.
    """
    from main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
