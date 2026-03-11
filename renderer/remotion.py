"""RemotionRenderer — HTTP client implementation of VideoRendererProtocol."""

from __future__ import annotations

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

    async def render(self, request: RenderRequest) -> str:
        """Submit a render job to the Remotion service, return job_id."""
        import httpx

        payload = {
            "sourceVideoUrl": request.source_video_url,
            "hookText": request.hook_text,
            "bodyText": request.body_text,
            "textDirection": request.text_direction,
            "animationStyle": request.animation_style,
            "durationInSeconds": request.duration_in_seconds,
        }
        if request.callback_url is not None:
            payload["callbackUrl"] = request.callback_url

        async with httpx.AsyncClient(timeout=10) as client:
            resp = client.post(f"{self.base_url}/renders", json=payload)
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
