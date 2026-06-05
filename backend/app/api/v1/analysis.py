import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db
from app.models.channel import Channel
from app.models.engagement_data import EngagementSnapshot, VideoSegment
from app.models.user import User
from app.models.video import Video
from app.models.video_analysis import VideoAnalysis
from app.utils.exceptions import NotFoundError

router = APIRouter(prefix="/videos/{video_id}", tags=["analysis"])


@router.get("/analysis")
async def get_analysis(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video_result = await db.execute(
        select(Video).join(Channel).where(Video.id == video_id, Channel.user_id == current_user.id)
    )
    video = video_result.scalar_one_or_none()
    if not video:
        raise NotFoundError(message=f"Video {video_id} not found")

    analysis_result = await db.execute(
        select(VideoAnalysis).where(VideoAnalysis.video_id == video_id)
    )
    analysis = analysis_result.scalar_one_or_none()

    segments_result = await db.execute(
        select(VideoSegment)
        .where(VideoSegment.video_id == video_id)
        .order_by(VideoSegment.segment_index)
    )
    segments = segments_result.scalars().all()

    detected_labels = []
    shot_count = 0
    if analysis:
        if analysis.labels and isinstance(analysis.labels, list):
            detected_labels = [l.get("description", "") for l in analysis.labels[:20]]
        if analysis.shot_changes and isinstance(analysis.shot_changes, list):
            shot_count = len(analysis.shot_changes)

    duration_minutes = (video.duration_seconds / 60) if video.duration_seconds else 1
    avg_pacing = shot_count / duration_minutes if duration_minutes > 0 else 0

    return {
        "segments": [
            {
                "id": str(s.id),
                "segment_index": s.segment_index,
                "start_ms": s.start_ms,
                "end_ms": s.end_ms,
                "segment_type": s.segment_type,
                "labels": s.labels,
                "pacing_score": s.pacing_score,
            }
            for s in segments
        ],
        "shot_count": shot_count,
        "avg_pacing": round(avg_pacing, 2),
        "detected_labels": detected_labels,
        "transcript_available": analysis is not None and analysis.transcript is not None,
    }


@router.get("/analysis/transcript")
async def get_transcript(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video_result = await db.execute(
        select(Video).join(Channel).where(Video.id == video_id, Channel.user_id == current_user.id)
    )
    if not video_result.scalar_one_or_none():
        raise NotFoundError(message=f"Video {video_id} not found")

    analysis_result = await db.execute(
        select(VideoAnalysis).where(VideoAnalysis.video_id == video_id)
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis or not analysis.transcript:
        raise NotFoundError(message="Transcript not available for this video")

    return {"segments": analysis.transcript}


@router.get("/engagement")
async def get_engagement(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video_result = await db.execute(
        select(Video).join(Channel).where(Video.id == video_id, Channel.user_id == current_user.id)
    )
    video = video_result.scalar_one_or_none()
    if not video:
        raise NotFoundError(message=f"Video {video_id} not found")

    engagement_result = await db.execute(
        select(EngagementSnapshot).where(EngagementSnapshot.video_id == video_id)
    )
    engagement = engagement_result.scalar_one_or_none()
    if not engagement:
        raise NotFoundError(message="Engagement data not yet available")

    # Map retention curve points to absolute timestamps
    retention_with_timestamps = []
    if engagement.retention_curve and video.duration_seconds:
        duration_ms = video.duration_seconds * 1000
        for i, point in enumerate(engagement.retention_curve):
            position_ratio = i / max(len(engagement.retention_curve) - 1, 1)
            retention_with_timestamps.append({
                "position_ratio": position_ratio,
                "timestamp_ms": int(position_ratio * duration_ms),
                "watch_ratio": point.get("watch_ratio"),
                "relative_performance": point.get("relative_retention"),
            })

    return {
        "overview": {
            "views": engagement.views,
            "likes": engagement.likes,
            "comments": engagement.comments,
            "shares": engagement.shares,
            "avg_view_duration_seconds": engagement.avg_view_duration_seconds,
            "avg_view_percentage": engagement.avg_view_percentage,
        },
        "retention_curve": retention_with_timestamps,
        "traffic_sources": engagement.traffic_sources,
        "demographics": engagement.demographics,
    }


@router.get("/engagement/segments")
async def get_engagement_segments(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video_result = await db.execute(
        select(Video).join(Channel).where(Video.id == video_id, Channel.user_id == current_user.id)
    )
    if not video_result.scalar_one_or_none():
        raise NotFoundError(message=f"Video {video_id} not found")

    segments_result = await db.execute(
        select(VideoSegment)
        .options(selectinload(VideoSegment.engagement))
        .where(VideoSegment.video_id == video_id)
        .order_by(VideoSegment.segment_index)
    )
    segments = segments_result.scalars().all()

    return [
        {
            "segment_id": str(s.id),
            "segment_index": s.segment_index,
            "start_ms": s.start_ms,
            "end_ms": s.end_ms,
            "segment_type": s.segment_type,
            "avg_retention": s.engagement.avg_retention if s.engagement else None,
            "retention_delta": s.engagement.retention_delta if s.engagement else None,
            "engagement_label": s.engagement.engagement_label if s.engagement else None,
        }
        for s in segments
    ]
