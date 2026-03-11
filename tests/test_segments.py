"""Unit tests for TextSegment model and segment-aware RenderRequest validation.

Tests cover:
- TextSegment field-level constraints (text, start_seconds, end_seconds, role, animation_style)
- TextSegment cross-field validator (end_seconds > start_seconds)
- RenderRequest with segments: count 1-5, no overlap, timing within duration
- RenderRequest legacy mode (hook_text + body_text, no segments)
- RenderRequest neither/both modes
"""

import pytest
from pydantic import ValidationError

from renderer.models import TextSegment, RenderRequest


# ---------------------------------------------------------------------------
# TextSegment — field-level tests
# ---------------------------------------------------------------------------


class TestTextSegment:

    def test_valid_segment_succeeds(self):
        """TextSegment with valid fields creates successfully."""
        seg = TextSegment(text="hello", start_seconds=0.0, end_seconds=3.0, role="hook")
        assert seg.text == "hello"
        assert seg.start_seconds == 0.0
        assert seg.end_seconds == 3.0
        assert seg.role == "hook"

    def test_default_animation_style_is_fade(self):
        """TextSegment default animation_style is 'fade'."""
        seg = TextSegment(text="hi", start_seconds=0.0, end_seconds=2.0, role="body")
        assert seg.animation_style == "fade"

    def test_explicit_animation_style_slide(self):
        """TextSegment accepts 'slide' animation_style."""
        seg = TextSegment(text="hi", start_seconds=0.0, end_seconds=2.0, role="body", animation_style="slide")
        assert seg.animation_style == "slide"

    def test_role_hook_accepted(self):
        """TextSegment accepts 'hook' role."""
        seg = TextSegment(text="x", start_seconds=0.0, end_seconds=1.0, role="hook")
        assert seg.role == "hook"

    def test_role_body_accepted(self):
        """TextSegment accepts 'body' role."""
        seg = TextSegment(text="x", start_seconds=0.0, end_seconds=1.0, role="body")
        assert seg.role == "body"

    def test_role_cta_accepted(self):
        """TextSegment accepts 'cta' role."""
        seg = TextSegment(text="x", start_seconds=0.0, end_seconds=1.0, role="cta")
        assert seg.role == "cta"

    def test_end_before_start_raises_value_error(self):
        """TextSegment with end_seconds <= start_seconds raises ValidationError."""
        with pytest.raises(ValidationError):
            TextSegment(text="hello", start_seconds=3.0, end_seconds=1.0, role="hook")

    def test_end_equal_to_start_raises_value_error(self):
        """TextSegment with end_seconds == start_seconds raises ValidationError."""
        with pytest.raises(ValidationError):
            TextSegment(text="hello", start_seconds=2.0, end_seconds=2.0, role="hook")

    def test_negative_start_seconds_raises_value_error(self):
        """TextSegment with negative start_seconds raises ValidationError."""
        with pytest.raises(ValidationError):
            TextSegment(text="hello", start_seconds=-1.0, end_seconds=3.0, role="hook")

    def test_invalid_role_raises_value_error(self):
        """TextSegment with invalid role raises ValidationError."""
        with pytest.raises(ValidationError):
            TextSegment(text="hello", start_seconds=0.0, end_seconds=3.0, role="invalid")

    def test_invalid_animation_style_raises_value_error(self):
        """TextSegment with invalid animation_style raises ValidationError."""
        with pytest.raises(ValidationError):
            TextSegment(text="hi", start_seconds=0.0, end_seconds=2.0, role="body", animation_style="bounce")

    def test_zero_start_seconds_accepted(self):
        """TextSegment with start_seconds=0.0 is valid (boundary)."""
        seg = TextSegment(text="hi", start_seconds=0.0, end_seconds=5.0, role="hook")
        assert seg.start_seconds == 0.0

    def test_integer_seconds_accepted(self):
        """TextSegment coerces integer seconds to float."""
        seg = TextSegment(text="hi", start_seconds=0, end_seconds=3, role="hook")
        assert seg.start_seconds == 0.0
        assert seg.end_seconds == 3.0


# ---------------------------------------------------------------------------
# RenderRequest — segments validation
# ---------------------------------------------------------------------------


class TestRenderRequestWithSegments:

    def _make_segment(self, start: float, end: float, role: str = "body") -> TextSegment:
        return TextSegment(text="test", start_seconds=start, end_seconds=end, role=role)

    def test_three_valid_segments_passes(self):
        """RenderRequest with 3 valid non-overlapping segments passes validation."""
        segs = [
            self._make_segment(0.0, 5.0, "hook"),
            self._make_segment(5.0, 10.0, "body"),
            self._make_segment(10.0, 15.0, "cta"),
        ]
        req = RenderRequest(
            source_video_url="https://example.com/v.mp4",
            record_id="recXYZ",
            segments=segs,
            duration_in_seconds=15,
        )
        assert len(req.segments) == 3

    def test_one_segment_passes(self):
        """RenderRequest with 1 segment passes (minimum count)."""
        req = RenderRequest(
            source_video_url="https://example.com/v.mp4",
            record_id="recXYZ",
            segments=[self._make_segment(0.0, 15.0, "hook")],
        )
        assert len(req.segments) == 1

    def test_five_segments_passes(self):
        """RenderRequest with 5 segments passes (maximum count)."""
        segs = [self._make_segment(i * 3.0, (i + 1) * 3.0) for i in range(5)]
        req = RenderRequest(
            source_video_url="https://example.com/v.mp4",
            record_id="recXYZ",
            segments=segs,
            duration_in_seconds=15,
        )
        assert len(req.segments) == 5

    def test_six_segments_raises_value_error(self):
        """RenderRequest with 6 segments raises ValidationError (max is 5)."""
        segs = [self._make_segment(i * 2.0, (i + 1) * 2.0) for i in range(6)]
        with pytest.raises(ValidationError):
            RenderRequest(
                source_video_url="https://example.com/v.mp4",
                record_id="recXYZ",
                segments=segs,
                duration_in_seconds=20,
            )

    def test_empty_segments_raises_value_error(self):
        """RenderRequest with segments=[] raises ValidationError (min is 1)."""
        with pytest.raises(ValidationError):
            RenderRequest(
                source_video_url="https://example.com/v.mp4",
                record_id="recXYZ",
                segments=[],
            )

    def test_overlapping_segments_raises_value_error(self):
        """RenderRequest with overlapping segments raises ValidationError."""
        segs = [
            self._make_segment(0.0, 6.0, "hook"),
            self._make_segment(4.0, 10.0, "body"),  # overlap: starts before seg[0] ends
        ]
        with pytest.raises(ValidationError):
            RenderRequest(
                source_video_url="https://example.com/v.mp4",
                record_id="recXYZ",
                segments=segs,
                duration_in_seconds=15,
            )

    def test_segment_end_exceeds_duration_raises_value_error(self):
        """RenderRequest where segment end_seconds > duration_in_seconds raises ValidationError."""
        segs = [self._make_segment(0.0, 20.0, "hook")]
        with pytest.raises(ValidationError):
            RenderRequest(
                source_video_url="https://example.com/v.mp4",
                record_id="recXYZ",
                segments=segs,
                duration_in_seconds=15,
            )

    def test_segment_end_exactly_at_duration_passes(self):
        """RenderRequest where segment end_seconds == duration_in_seconds passes."""
        req = RenderRequest(
            source_video_url="https://example.com/v.mp4",
            record_id="recXYZ",
            segments=[self._make_segment(0.0, 15.0, "hook")],
            duration_in_seconds=15,
        )
        assert req.segments[0].end_seconds == 15.0

    def test_adjacent_segments_pass(self):
        """RenderRequest with touching (non-overlapping) segments passes."""
        segs = [
            self._make_segment(0.0, 7.5, "hook"),
            self._make_segment(7.5, 15.0, "body"),
        ]
        req = RenderRequest(
            source_video_url="https://example.com/v.mp4",
            record_id="recXYZ",
            segments=segs,
            duration_in_seconds=15,
        )
        assert len(req.segments) == 2


# ---------------------------------------------------------------------------
# RenderRequest — legacy mode (hook_text + body_text)
# ---------------------------------------------------------------------------


class TestRenderRequestLegacyMode:

    def test_legacy_hook_and_body_text_passes(self):
        """RenderRequest with hook_text and body_text (no segments) passes validation."""
        req = RenderRequest(
            source_video_url="https://example.com/v.mp4",
            hook_text="x",
            body_text="y",
            record_id="recABC",
        )
        assert req.hook_text == "x"
        assert req.body_text == "y"
        assert req.segments is None

    def test_neither_segments_nor_legacy_fields_raises_value_error(self):
        """RenderRequest with neither hook_text/body_text nor segments raises ValidationError."""
        with pytest.raises(ValidationError):
            RenderRequest(
                source_video_url="https://example.com/v.mp4",
                record_id="recABC",
            )

    def test_only_hook_text_without_body_text_raises_value_error(self):
        """RenderRequest with only hook_text (no body_text, no segments) raises ValidationError."""
        with pytest.raises(ValidationError):
            RenderRequest(
                source_video_url="https://example.com/v.mp4",
                record_id="recABC",
                hook_text="hook only",
            )

    def test_only_body_text_without_hook_text_raises_value_error(self):
        """RenderRequest with only body_text (no hook_text, no segments) raises ValidationError."""
        with pytest.raises(ValidationError):
            RenderRequest(
                source_video_url="https://example.com/v.mp4",
                record_id="recABC",
                body_text="body only",
            )

    def test_both_segments_and_legacy_fields_is_valid(self):
        """RenderRequest with both segments AND hook_text/body_text: segments take priority (valid)."""
        seg = TextSegment(text="hi", start_seconds=0.0, end_seconds=15.0, role="hook")
        req = RenderRequest(
            source_video_url="https://example.com/v.mp4",
            record_id="recABC",
            hook_text="legacy hook",
            body_text="legacy body",
            segments=[seg],
            duration_in_seconds=15,
        )
        assert req.segments is not None
        assert len(req.segments) == 1
        assert req.hook_text == "legacy hook"
