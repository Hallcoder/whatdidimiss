from __future__ import annotations

import logging
from typing import Optional

from app.services.video_intelligence_service import (
    LabelAnnotation,
    ShotChange,
    TranscriptSegment,
    VideoIntelligenceResult,
)

logger = logging.getLogger(__name__)

# Segments shorter than this (ms) get merged into the previous segment
MIN_SEGMENT_DURATION_MS = 3000

# The first N ms of a video are considered the "hook" zone
HOOK_ZONE_MS = 30000

# The last N ms of a video are considered the "outro/CTA" zone
CTA_ZONE_MS = 30000


def derive_segments(
    vi_result: VideoIntelligenceResult,
    duration_ms: int,
) -> list[dict]:
    """Derive meaningful video segments from Video Intelligence results.

    Groups shot changes into segments, assigns types, slices transcript,
    and computes pacing scores.

    Returns a list of dicts ready to be inserted as VideoSegment rows:
        {segment_index, start_ms, end_ms, segment_type, labels, transcript_text, pacing_score}
    """
    shots = vi_result.shot_changes

    if not shots:
        # No shot changes detected — treat the whole video as one segment
        return [_build_segment(
            index=0,
            start_ms=0,
            end_ms=duration_ms,
            shot_count=1,
            labels=vi_result.labels,
            transcript=vi_result.transcript,
            duration_ms=duration_ms,
        )]

    # Step 1: Merge very short shots into clusters
    clusters = _cluster_shots(shots, MIN_SEGMENT_DURATION_MS)

    # Step 2: Build segment dicts
    segments = []
    for i, (cluster_start, cluster_end, shot_count) in enumerate(clusters):
        seg = _build_segment(
            index=i,
            start_ms=cluster_start,
            end_ms=cluster_end,
            shot_count=shot_count,
            labels=vi_result.labels,
            transcript=vi_result.transcript,
            duration_ms=duration_ms,
        )
        segments.append(seg)

    # Step 3: Assign segment types based on position
    _assign_segment_types(segments, duration_ms)

    return segments


def _cluster_shots(shots: list[ShotChange], min_duration_ms: int) -> list[tuple]:
    """Cluster consecutive short shots into larger segments.

    Returns list of (start_ms, end_ms, shot_count) tuples.
    """
    if not shots:
        return []

    clusters = []
    current_start = shots[0].start_ms
    current_end = shots[0].end_ms
    current_shot_count = 1

    for shot in shots[1:]:
        duration_so_far = shot.end_ms - current_start

        # If adding this shot keeps us under the minimum, merge it
        if (current_end - current_start) < min_duration_ms:
            current_end = shot.end_ms
            current_shot_count += 1
        else:
            # Current cluster is big enough, start a new one
            clusters.append((current_start, current_end, current_shot_count))
            current_start = shot.start_ms
            current_end = shot.end_ms
            current_shot_count = 1

    # Don't forget the last cluster
    clusters.append((current_start, current_end, current_shot_count))

    # Merge the final cluster if it's too short
    if len(clusters) > 1 and (clusters[-1][1] - clusters[-1][0]) < min_duration_ms:
        last = clusters.pop()
        prev_start, prev_end, prev_count = clusters.pop()
        clusters.append((prev_start, last[1], prev_count + last[2]))

    return clusters


def _build_segment(
    index: int,
    start_ms: int,
    end_ms: int,
    shot_count: int,
    labels: list[LabelAnnotation],
    transcript: list[TranscriptSegment],
    duration_ms: int,
) -> dict:
    """Build a single segment dict with labels, transcript, and pacing."""
    # Find labels that overlap with this segment's time range
    segment_labels = _labels_for_range(labels, start_ms, end_ms)

    # Slice transcript for this segment
    transcript_text = _transcript_for_range(transcript, start_ms, end_ms)

    # Pacing: shots per minute
    duration_minutes = max((end_ms - start_ms) / 60000, 0.001)
    pacing_score = round(shot_count / duration_minutes, 2)

    return {
        "segment_index": index,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "segment_type": None,  # assigned later by _assign_segment_types
        "labels": segment_labels,
        "transcript_text": transcript_text if transcript_text else None,
        "pacing_score": pacing_score,
    }


def _labels_for_range(
    labels: list[LabelAnnotation], start_ms: int, end_ms: int
) -> list[str]:
    """Find label descriptions that overlap with the given time range."""
    matching = []
    for label in labels:
        for seg in label.segments:
            seg_start = seg["start_ms"]
            seg_end = seg["end_ms"]
            # Check for overlap
            if seg_start < end_ms and seg_end > start_ms:
                if label.description not in matching:
                    matching.append(label.description)
                break
    # Return top 5 labels
    return matching[:5]


def _transcript_for_range(
    transcript: list[TranscriptSegment], start_ms: int, end_ms: int
) -> Optional[str]:
    """Concatenate transcript segments that fall within the time range."""
    parts = []
    for seg in transcript:
        # Check for overlap
        if seg.start_ms < end_ms and seg.end_ms > start_ms:
            parts.append(seg.text)

    if not parts:
        return None

    return " ".join(parts)


def _assign_segment_types(segments: list[dict], duration_ms: int) -> None:
    """Assign segment types based on position in the video.

    Types: intro_hook, main_content, transition, cta
    """
    if not segments:
        return

    for seg in segments:
        mid_point = (seg["start_ms"] + seg["end_ms"]) / 2

        if mid_point <= HOOK_ZONE_MS:
            seg["segment_type"] = "intro_hook"
        elif mid_point >= duration_ms - CTA_ZONE_MS:
            seg["segment_type"] = "cta"
        elif seg["pacing_score"] and seg["pacing_score"] > 15:
            # Very fast pacing suggests a transition or montage
            seg["segment_type"] = "transition"
        else:
            seg["segment_type"] = "main_content"

    # Override: first segment is always intro_hook
    segments[0]["segment_type"] = "intro_hook"

    # Override: last segment is always cta (if video is long enough)
    if len(segments) > 1 and duration_ms > 60000:
        segments[-1]["segment_type"] = "cta"
