"""Tests for renderer protocol compliance and model validation."""

import pytest
from renderer import VideoRendererProtocol, RenderRequest, JobStatus
from renderer import RemotionRenderer
import config


# ---------------------------------------------------------------------------
# RenderRequest model validation
# ---------------------------------------------------------------------------

class TestRenderRequestValidation:

    def test_render_request_valid_required_fields(self):
        """RenderRequest validates with all required fields."""
        req = RenderRequest(
            source_video_url="https://example.com/video.mp4",
            hook_text="Amazing hook!",
            body_text="Body content here.",
            record_id="rec123",
        )
        assert req.source_video_url == "https://example.com/video.mp4"
        assert req.hook_text == "Amazing hook!"
        assert req.body_text == "Body content here."
        assert req.record_id == "rec123"

    def test_render_request_rejects_missing_source_video_url(self):
        """RenderRequest rejects a missing source_video_url."""
        with pytest.raises(Exception):
            RenderRequest(
                hook_text="hook",
                body_text="body",
                record_id="rec123",
            )

    def test_render_request_rejects_missing_hook_text(self):
        """RenderRequest rejects a missing hook_text."""
        with pytest.raises(Exception):
            RenderRequest(
                source_video_url="https://example.com/video.mp4",
                body_text="body",
                record_id="rec123",
            )

    def test_render_request_rejects_missing_body_text(self):
        """RenderRequest rejects a missing body_text."""
        with pytest.raises(Exception):
            RenderRequest(
                source_video_url="https://example.com/video.mp4",
                hook_text="hook",
                record_id="rec123",
            )

    def test_render_request_rejects_missing_record_id(self):
        """RenderRequest rejects a missing record_id."""
        with pytest.raises(Exception):
            RenderRequest(
                source_video_url="https://example.com/video.mp4",
                hook_text="hook",
                body_text="body",
            )

    def test_render_request_defaults_text_direction_rtl(self):
        """RenderRequest defaults text_direction to 'rtl'."""
        req = RenderRequest(
            source_video_url="https://example.com/video.mp4",
            hook_text="hook",
            body_text="body",
            record_id="rec123",
        )
        assert req.text_direction == "rtl"

    def test_render_request_defaults_animation_style_fade(self):
        """RenderRequest defaults animation_style to 'fade'."""
        req = RenderRequest(
            source_video_url="https://example.com/video.mp4",
            hook_text="hook",
            body_text="body",
            record_id="rec123",
        )
        assert req.animation_style == "fade"

    def test_render_request_defaults_duration_15(self):
        """RenderRequest defaults duration_in_seconds to 15."""
        req = RenderRequest(
            source_video_url="https://example.com/video.mp4",
            hook_text="hook",
            body_text="body",
            record_id="rec123",
        )
        assert req.duration_in_seconds == 15

    def test_render_request_defaults_callback_url_none(self):
        """RenderRequest defaults callback_url to None."""
        req = RenderRequest(
            source_video_url="https://example.com/video.mp4",
            hook_text="hook",
            body_text="body",
            record_id="rec123",
        )
        assert req.callback_url is None

    def test_render_request_accepts_ltr_direction(self):
        """RenderRequest accepts text_direction='ltr'."""
        req = RenderRequest(
            source_video_url="https://example.com/video.mp4",
            hook_text="hook",
            body_text="body",
            record_id="rec123",
            text_direction="ltr",
        )
        assert req.text_direction == "ltr"

    def test_render_request_rejects_invalid_text_direction(self):
        """RenderRequest rejects invalid text_direction values."""
        with pytest.raises(Exception):
            RenderRequest(
                source_video_url="https://example.com/video.mp4",
                hook_text="hook",
                body_text="body",
                record_id="rec123",
                text_direction="invalid",
            )

    def test_render_request_accepts_slide_animation(self):
        """RenderRequest accepts animation_style='slide'."""
        req = RenderRequest(
            source_video_url="https://example.com/video.mp4",
            hook_text="hook",
            body_text="body",
            record_id="rec123",
            animation_style="slide",
        )
        assert req.animation_style == "slide"

    def test_render_request_rejects_invalid_animation_style(self):
        """RenderRequest rejects invalid animation_style values."""
        with pytest.raises(Exception):
            RenderRequest(
                source_video_url="https://example.com/video.mp4",
                hook_text="hook",
                body_text="body",
                record_id="rec123",
                animation_style="spin",
            )

    def test_render_request_rejects_duration_below_min(self):
        """RenderRequest rejects duration_in_seconds below 3."""
        with pytest.raises(Exception):
            RenderRequest(
                source_video_url="https://example.com/video.mp4",
                hook_text="hook",
                body_text="body",
                record_id="rec123",
                duration_in_seconds=2,
            )

    def test_render_request_rejects_duration_above_max(self):
        """RenderRequest rejects duration_in_seconds above 600."""
        with pytest.raises(Exception):
            RenderRequest(
                source_video_url="https://example.com/video.mp4",
                hook_text="hook",
                body_text="body",
                record_id="rec123",
                duration_in_seconds=601,
            )


# ---------------------------------------------------------------------------
# JobStatus model validation
# ---------------------------------------------------------------------------

class TestJobStatusValidation:

    def test_job_status_accepts_accepted_state(self):
        """JobStatus accepts 'accepted' state."""
        status = JobStatus(state="accepted")
        assert status.state == "accepted"

    def test_job_status_accepts_rendering_state(self):
        """JobStatus accepts 'rendering' state."""
        status = JobStatus(state="rendering")
        assert status.state == "rendering"

    def test_job_status_accepts_downloading_state(self):
        """JobStatus accepts 'downloading' state."""
        status = JobStatus(state="downloading")
        assert status.state == "downloading"

    def test_job_status_accepts_uploading_state(self):
        """JobStatus accepts 'uploading' state."""
        status = JobStatus(state="uploading")
        assert status.state == "uploading"

    def test_job_status_accepts_completed_state(self):
        """JobStatus accepts 'completed' state."""
        status = JobStatus(state="completed")
        assert status.state == "completed"

    def test_job_status_accepts_failed_state(self):
        """JobStatus accepts 'failed' state."""
        status = JobStatus(state="failed")
        assert status.state == "failed"

    def test_job_status_accepts_timed_out_state(self):
        """JobStatus accepts 'timed_out' state."""
        status = JobStatus(state="timed_out")
        assert status.state == "timed_out"

    def test_job_status_rejects_invalid_state(self):
        """JobStatus rejects an invalid state value."""
        with pytest.raises(Exception):
            JobStatus(state="unknown")

    def test_job_status_video_url_is_optional(self):
        """JobStatus.video_url is None by default (not completed)."""
        status = JobStatus(state="rendering")
        assert status.video_url is None

    def test_job_status_video_url_accepts_string(self):
        """JobStatus.video_url accepts a URL string when completed."""
        status = JobStatus(state="completed", video_url="https://cdn.example.com/output.mp4")
        assert status.video_url == "https://cdn.example.com/output.mp4"

    def test_job_status_error_is_optional(self):
        """JobStatus.error is None by default."""
        status = JobStatus(state="accepted")
        assert status.error is None

    def test_job_status_progress_defaults_zero(self):
        """JobStatus.progress defaults to 0.0."""
        status = JobStatus(state="accepted")
        assert status.progress == 0.0


# ---------------------------------------------------------------------------
# VideoRendererProtocol compliance (structural typing)
# ---------------------------------------------------------------------------

class TestProtocolCompliance:

    def test_remotion_implements_protocol(self):
        """RemotionRenderer satisfies VideoRendererProtocol via isinstance()."""
        renderer = RemotionRenderer()
        assert isinstance(renderer, VideoRendererProtocol)

    def test_protocol_swappability(self):
        """A DummyRenderer with matching signatures satisfies VideoRendererProtocol.

        This proves structural typing works — swapping the render engine
        requires zero code changes in calling code.
        """

        class DummyRenderer:
            async def render(self, request: RenderRequest) -> str:
                return "dummy-job-id"

            async def get_status(self, job_id: str) -> JobStatus:
                return JobStatus(state="completed")

            async def health_check(self) -> bool:
                return True

            async def download_file(self, job_id: str, dest_path: str) -> None:
                pass

        assert isinstance(DummyRenderer(), VideoRendererProtocol)

    def test_remotion_default_base_url(self):
        """RemotionRenderer defaults base_url to config.REMOTION_SERVICE_URL."""
        renderer = RemotionRenderer()
        assert renderer.base_url == config.REMOTION_SERVICE_URL

    def test_remotion_custom_base_url(self):
        """RemotionRenderer accepts a custom base_url."""
        renderer = RemotionRenderer("http://custom:9999")
        assert renderer.base_url == "http://custom:9999"
