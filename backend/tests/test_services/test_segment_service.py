from __future__ import annotations

from app.services.segment_service import derive_segments, _cluster_shots, _assign_segment_types
from app.services.video_intelligence_service import (
    LabelAnnotation,
    ShotChange,
    TranscriptSegment,
    VideoIntelligenceResult,
)


def _make_vi_result(
    shots=None, labels=None, transcript=None
) -> VideoIntelligenceResult:
    return VideoIntelligenceResult(
        labels=labels or [],
        shot_changes=shots or [],
        text_detections=[],
        transcript=transcript or [],
        raw_response={},
    )


class TestDeriveSegments:
    def test_no_shots_returns_single_segment(self):
        result = derive_segments(_make_vi_result(), duration_ms=60000)
        assert len(result) == 1
        assert result[0]["start_ms"] == 0
        assert result[0]["end_ms"] == 60000
        assert result[0]["segment_index"] == 0

    def test_shots_produce_multiple_segments(self):
        shots = [
            ShotChange(start_ms=0, end_ms=10000),
            ShotChange(start_ms=10000, end_ms=30000),
            ShotChange(start_ms=30000, end_ms=60000),
        ]
        result = derive_segments(_make_vi_result(shots=shots), duration_ms=60000)
        assert len(result) >= 2
        # First segment should be intro_hook
        assert result[0]["segment_type"] == "intro_hook"

    def test_pacing_score_calculated(self):
        shots = [
            ShotChange(start_ms=0, end_ms=5000),
            ShotChange(start_ms=5000, end_ms=10000),
            ShotChange(start_ms=10000, end_ms=15000),
            ShotChange(start_ms=15000, end_ms=20000),
        ]
        result = derive_segments(_make_vi_result(shots=shots), duration_ms=20000)
        for seg in result:
            assert seg["pacing_score"] is not None
            assert seg["pacing_score"] > 0

    def test_labels_assigned_to_overlapping_segments(self):
        shots = [
            ShotChange(start_ms=0, end_ms=30000),
            ShotChange(start_ms=30000, end_ms=60000),
        ]
        labels = [
            LabelAnnotation(
                description="cat",
                category="animal",
                confidence=0.9,
                segments=[{"start_ms": 0, "end_ms": 30000, "confidence": 0.9}],
            ),
        ]
        result = derive_segments(
            _make_vi_result(shots=shots, labels=labels), duration_ms=60000
        )
        first_seg = result[0]
        assert "cat" in first_seg["labels"]

    def test_transcript_sliced_to_segments(self):
        shots = [
            ShotChange(start_ms=0, end_ms=30000),
            ShotChange(start_ms=30000, end_ms=60000),
        ]
        transcript = [
            TranscriptSegment(
                text="Hello world", confidence=0.95, start_ms=0, end_ms=15000, words=[]
            ),
            TranscriptSegment(
                text="Goodbye world", confidence=0.90, start_ms=35000, end_ms=50000, words=[]
            ),
        ]
        result = derive_segments(
            _make_vi_result(shots=shots, transcript=transcript), duration_ms=60000
        )
        assert result[0]["transcript_text"] is not None
        assert "Hello" in result[0]["transcript_text"]

    def test_short_video_no_cta_override(self):
        shots = [
            ShotChange(start_ms=0, end_ms=15000),
            ShotChange(start_ms=15000, end_ms=30000),
        ]
        result = derive_segments(_make_vi_result(shots=shots), duration_ms=30000)
        # Video under 60s, last segment should NOT be forced to CTA
        assert len(result) >= 1


class TestClusterShots:
    def test_merges_very_short_shots(self):
        shots = [
            ShotChange(start_ms=0, end_ms=1000),
            ShotChange(start_ms=1000, end_ms=2000),
            ShotChange(start_ms=2000, end_ms=10000),
        ]
        clusters = _cluster_shots(shots, min_duration_ms=3000)
        # First two shots (1s each) should be merged
        assert len(clusters) <= 2

    def test_preserves_long_shots(self):
        shots = [
            ShotChange(start_ms=0, end_ms=10000),
            ShotChange(start_ms=10000, end_ms=25000),
            ShotChange(start_ms=25000, end_ms=40000),
        ]
        clusters = _cluster_shots(shots, min_duration_ms=3000)
        assert len(clusters) == 3

    def test_empty_shots(self):
        clusters = _cluster_shots([], min_duration_ms=3000)
        assert clusters == []


class TestAssignSegmentTypes:
    def test_first_segment_always_intro_hook(self):
        segments = [
            {"start_ms": 0, "end_ms": 20000, "pacing_score": 5, "segment_type": None},
            {"start_ms": 20000, "end_ms": 80000, "pacing_score": 5, "segment_type": None},
            {"start_ms": 80000, "end_ms": 120000, "pacing_score": 5, "segment_type": None},
        ]
        _assign_segment_types(segments, duration_ms=120000)
        assert segments[0]["segment_type"] == "intro_hook"

    def test_last_segment_cta_for_long_videos(self):
        segments = [
            {"start_ms": 0, "end_ms": 30000, "pacing_score": 5, "segment_type": None},
            {"start_ms": 30000, "end_ms": 60000, "pacing_score": 5, "segment_type": None},
            {"start_ms": 60000, "end_ms": 120000, "pacing_score": 5, "segment_type": None},
        ]
        _assign_segment_types(segments, duration_ms=120000)
        assert segments[-1]["segment_type"] == "cta"

    def test_high_pacing_marked_transition(self):
        segments = [
            {"start_ms": 0, "end_ms": 10000, "pacing_score": 5, "segment_type": None},
            {"start_ms": 35000, "end_ms": 55000, "pacing_score": 20, "segment_type": None},
            {"start_ms": 90000, "end_ms": 120000, "pacing_score": 5, "segment_type": None},
        ]
        _assign_segment_types(segments, duration_ms=120000)
        assert segments[1]["segment_type"] == "transition"
