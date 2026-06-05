from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.services.youtube_analytics_service import RetentionPoint

logger = logging.getLogger(__name__)

# Thresholds for labeling segments
HIGH_RETENTION_THRESHOLD = 0.7    # avg retention above 70% of initial viewers
DROP_OFF_DELTA_THRESHOLD = -0.10  # retention drops more than 10pp across segment
SPIKE_DELTA_THRESHOLD = 0.05      # retention increases more than 5pp (unusual, indicates hook)


@dataclass
class SegmentEngagementData:
    segment_id: str
    avg_retention: float
    retention_delta: float
    relative_performance: float
    engagement_label: str


class EngagementCorrelationService:
    """Maps YouTube Analytics retention data to video segments."""

    def correlate(
        self,
        retention_curve: list[RetentionPoint],
        segments: list[dict],
        duration_ms: int,
    ) -> list[SegmentEngagementData]:
        """Map retention data points to segments and compute engagement metrics.

        Args:
            retention_curve: 100 data points from YouTube Analytics
            segments: list of dicts with keys: id, start_ms, end_ms
            duration_ms: total video duration in milliseconds

        Returns:
            list of SegmentEngagementData, one per segment
        """
        if not retention_curve or not segments or duration_ms <= 0:
            logger.warning("Insufficient data for correlation: %d points, %d segments, %d ms",
                           len(retention_curve), len(segments), duration_ms)
            return []

        results = []

        for seg in segments:
            seg_start_ms = seg["start_ms"]
            seg_end_ms = seg["end_ms"]

            # Find retention points that fall within this segment's time range
            points_in_range = _points_for_range(
                retention_curve, seg_start_ms, seg_end_ms, duration_ms
            )

            if not points_in_range:
                # Segment is too short to contain any retention data points
                # Interpolate from nearest points
                avg_ret, delta, rel_perf = _interpolate_for_range(
                    retention_curve, seg_start_ms, seg_end_ms, duration_ms
                )
            else:
                ratios = [p.audience_watch_ratio for p in points_in_range]
                relatives = [p.relative_retention for p in points_in_range]

                avg_ret = sum(ratios) / len(ratios)
                delta = ratios[-1] - ratios[0]
                rel_perf = sum(relatives) / len(relatives)

            label = _classify_segment(avg_ret, delta)

            results.append(SegmentEngagementData(
                segment_id=seg["id"],
                avg_retention=round(avg_ret, 4),
                retention_delta=round(delta, 4),
                relative_performance=round(rel_perf, 4),
                engagement_label=label,
            ))

        return results


def _points_for_range(
    curve: list[RetentionPoint],
    start_ms: int,
    end_ms: int,
    duration_ms: int,
) -> list[RetentionPoint]:
    """Get retention points whose timestamp falls within [start_ms, end_ms)."""
    start_ratio = start_ms / duration_ms
    end_ratio = end_ms / duration_ms

    return [
        p for p in curve
        if start_ratio <= p.elapsed_ratio < end_ratio
    ]


def _interpolate_for_range(
    curve: list[RetentionPoint],
    start_ms: int,
    end_ms: int,
    duration_ms: int,
) -> tuple:
    """Interpolate retention values for a segment that has no data points.

    Returns (avg_retention, delta, relative_performance).
    """
    if not curve:
        return (0.0, 0.0, 1.0)

    start_ratio = start_ms / duration_ms
    end_ratio = end_ms / duration_ms
    mid_ratio = (start_ratio + end_ratio) / 2

    # Find the two nearest points
    closest = min(curve, key=lambda p: abs(p.elapsed_ratio - mid_ratio))

    # Find points nearest to start and end for delta
    start_point = min(curve, key=lambda p: abs(p.elapsed_ratio - start_ratio))
    end_point = min(curve, key=lambda p: abs(p.elapsed_ratio - end_ratio))

    avg_ret = closest.audience_watch_ratio
    delta = end_point.audience_watch_ratio - start_point.audience_watch_ratio
    rel_perf = closest.relative_retention

    return (avg_ret, delta, rel_perf)


def _classify_segment(avg_retention: float, delta: float) -> str:
    """Classify a segment based on retention metrics."""
    if delta <= DROP_OFF_DELTA_THRESHOLD:
        return "drop_off"
    if delta >= SPIKE_DELTA_THRESHOLD:
        return "spike"
    if avg_retention >= HIGH_RETENTION_THRESHOLD:
        return "high_retention"
    return "steady"
