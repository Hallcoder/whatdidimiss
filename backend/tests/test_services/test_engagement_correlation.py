from __future__ import annotations

from app.services.engagement_correlation_service import (
    EngagementCorrelationService,
    _classify_segment,
)
from app.services.youtube_analytics_service import RetentionPoint


def _make_curve(n=100, base_ratio=0.8, decay=0.005):
    """Generate a synthetic retention curve that decays linearly."""
    return [
        RetentionPoint(
            elapsed_ratio=i / (n - 1),
            audience_watch_ratio=max(base_ratio - decay * i, 0.0),
            relative_retention=1.0,
        )
        for i in range(n)
    ]


class TestCorrelate:
    def test_basic_correlation(self):
        curve = _make_curve(100, base_ratio=0.9, decay=0.005)
        segments = [
            {"id": "seg-0", "start_ms": 0, "end_ms": 30000},
            {"id": "seg-1", "start_ms": 30000, "end_ms": 60000},
        ]
        service = EngagementCorrelationService()
        results = service.correlate(curve, segments, duration_ms=60000)

        assert len(results) == 2
        # First segment should have higher retention than second
        assert results[0].avg_retention > results[1].avg_retention

    def test_empty_curve_returns_empty(self):
        service = EngagementCorrelationService()
        results = service.correlate([], [{"id": "a", "start_ms": 0, "end_ms": 1000}], 1000)
        assert results == []

    def test_empty_segments_returns_empty(self):
        service = EngagementCorrelationService()
        results = service.correlate(_make_curve(), [], 60000)
        assert results == []

    def test_retention_delta_negative_for_decay(self):
        curve = _make_curve(100, base_ratio=1.0, decay=0.01)
        segments = [{"id": "seg-0", "start_ms": 0, "end_ms": 60000}]
        service = EngagementCorrelationService()
        results = service.correlate(curve, segments, duration_ms=60000)
        # With steady decay, delta should be negative
        assert results[0].retention_delta < 0

    def test_single_segment_whole_video(self):
        curve = _make_curve(100, base_ratio=0.8, decay=0.002)
        segments = [{"id": "all", "start_ms": 0, "end_ms": 120000}]
        service = EngagementCorrelationService()
        results = service.correlate(curve, segments, duration_ms=120000)
        assert len(results) == 1
        assert 0 < results[0].avg_retention <= 1.0


class TestClassifySegment:
    def test_drop_off(self):
        assert _classify_segment(avg_retention=0.5, delta=-0.15) == "drop_off"

    def test_spike(self):
        assert _classify_segment(avg_retention=0.6, delta=0.08) == "spike"

    def test_high_retention(self):
        assert _classify_segment(avg_retention=0.85, delta=-0.02) == "high_retention"

    def test_steady(self):
        assert _classify_segment(avg_retention=0.5, delta=-0.03) == "steady"
