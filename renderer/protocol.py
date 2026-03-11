"""VideoRendererProtocol — the abstract contract for render engine implementations."""

from typing import Protocol, runtime_checkable

from renderer.models import JobStatus, RenderRequest


@runtime_checkable
class VideoRendererProtocol(Protocol):
    """Structural protocol for renderer backends.

    Any class with these four async method signatures satisfies this protocol,
    enabling engine-swap without changing calling code (INTG-02).
    """

    async def render(self, request: RenderRequest) -> str:
        """Submit a render job and return the job_id."""
        ...

    async def get_status(self, job_id: str) -> JobStatus:
        """Poll job status by job_id."""
        ...

    async def health_check(self) -> bool:
        """Return True if the renderer service is reachable."""
        ...

    async def download_file(self, job_id: str, dest_path: str) -> None:
        """Download the rendered output file to dest_path."""
        ...
