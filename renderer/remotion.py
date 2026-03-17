"""RemotionRenderer — HTTP client implementation of VideoRendererProtocol."""

from __future__ import annotations

from typing import Any

import config
from renderer.models import JobStatus, RenderRequest

# State-to-state mapping from Remotion service terminology to internal states
_STATE_MAP: dict[str, str] = {
    "queued": "accepted",
    "in-progress": "rendering",
    "completed": "completed",
    "failed": "failed",
    "timed_out": "timed_out",
}


class RemotionRenderer:
    """HTTP client that calls the Remotion render service.

    Satisfies VideoRendererProtocol via structural typing (no explicit
    inheritance needed) — confirmed by isinstance(RemotionRenderer(), VideoRendererProtocol).
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url if base_url is not None else config.REMOTION_SERVICE_URL

    async def render(
        self,
        request: RenderRequest,
        resolved_brand: dict[str, Any] | None = None,
        segments: list[dict[str, Any]] | None = None,
    ) -> str:
        """Submit a render job to the Remotion service, return job_id.

        Args:
            request: The render request with video URL, text, and options.
            resolved_brand: Optional camelCase brand config dict from
                resolve_brand_for_render(). When provided, added to payload
                as 'brandConfig' for Zod validation in Remotion service.
                When absent, Remotion fills all brand defaults from schema.
            segments: Optional list of camelCase segment dicts from
                _build_segments(). When provided, sent as 'segments' payload
                instead of hookText/bodyText. When None (defensive fallback),
                falls back to legacy hookText/bodyText.
        """
        import httpx

        payload: dict[str, Any] = {
            "sourceVideoUrl": request.source_video_url,
            "textDirection": request.text_direction,
            "animationStyle": request.animation_style,
        }
        # Only include durationInSeconds when explicitly set.
        # When omitted, Remotion detects actual video duration via ffprobe.
        if request.duration_in_seconds is not None:
            payload["durationInSeconds"] = request.duration_in_seconds

        if segments is not None:
            # New path: send segments array; Zod validates via SegmentSchema
            payload["segments"] = segments
        else:
            # Defensive fallback: send legacy hookText/bodyText
            payload["hookText"] = request.hook_text
            payload["bodyText"] = request.body_text

        if request.callback_url is not None:
            payload["callbackUrl"] = request.callback_url
        if resolved_brand is not None:
            payload["brandConfig"] = resolved_brand

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{self.base_url}/renders", json=payload)
            resp.raise_for_status()
            return resp.json()["jobId"]

    async def get_status(self, job_id: str) -> JobStatus:
        """Poll render job status from the Remotion service."""
        import httpx

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/renders/{job_id}")
            resp.raise_for_status()
            data = resp.json()

        raw_state = data.get("state", "accepted")
        mapped_state = _STATE_MAP.get(raw_state, raw_state)

        return JobStatus(
            state=mapped_state,
            progress=data.get("progress", 0.0),
            video_url=data.get("videoUrl"),
            error=data.get("error"),
        )

    async def health_check(self) -> bool:
        """Return True if the Remotion service is reachable."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def download_file(self, job_id: str, dest_path: str) -> None:
        """Stream the rendered output file from the service to dest_path."""
        import httpx

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "GET", f"{self.base_url}/renders/{job_id}/file"
            ) as resp:
                resp.raise_for_status()
                with open(dest_path, "wb") as fh:
                    async for chunk in resp.aiter_bytes(chunk_size=8192):
                        fh.write(chunk)
