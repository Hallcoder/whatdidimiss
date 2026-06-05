import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db
from app.models.channel import Channel
from app.models.engagement_data import EngagementSnapshot, VideoSegment
from app.models.insight import Insight
from app.models.user import User
from app.models.video import Video
from app.utils.exceptions import NotFoundError

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/{video_id}")
async def get_dashboard(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Video)
        .join(Channel)
        .where(Video.id == video_id, Channel.user_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise NotFoundError(message=f"Video {video_id} not found")

    # Fetch insights
    insights_result = await db.execute(
        select(Insight)
        .where(Insight.video_id == video_id)
        .order_by(Insight.priority_rank)
    )
    all_insights = insights_result.scalars().all()

    wins = [i for i in all_insights if i.insight_type == "win"][:3]
    improvements = [i for i in all_insights if i.insight_type == "improvement"][:3]
    next_post_ideas = [i for i in all_insights if i.insight_type == "next_post"]
    creative_tweaks = [i for i in all_insights if i.insight_type == "creative_tweak"]

    # Analysis sections stored as JSON in raw_llm_response
    analysis_sections = {}
    for i in all_insights:
        if i.insight_type in ("script_analysis", "delivery_analysis", "visual_analysis", "audience_insights"):
            analysis_sections[i.insight_type] = i.raw_llm_response

    # Fetch engagement summary
    engagement_result = await db.execute(
        select(EngagementSnapshot).where(EngagementSnapshot.video_id == video_id)
    )
    engagement = engagement_result.scalar_one_or_none()

    # Fetch segments with engagement data for best/worst
    segments_result = await db.execute(
        select(VideoSegment)
        .options(selectinload(VideoSegment.engagement))
        .where(VideoSegment.video_id == video_id)
        .order_by(VideoSegment.segment_index)
    )
    segments = segments_result.scalars().all()

    best_segment = None
    worst_segment = None
    for seg in segments:
        if seg.engagement:
            if best_segment is None or (seg.engagement.avg_retention or 0) > (best_segment.engagement.avg_retention or 0):
                best_segment = seg
            if worst_segment is None or (seg.engagement.avg_retention or 0) < (worst_segment.engagement.avg_retention or 0):
                worst_segment = seg

    return {
        "video": {
            "id": str(video.id),
            "youtube_video_id": video.youtube_video_id,
            "title": video.title,
            "thumbnail_url": video.thumbnail_url,
            "duration_seconds": video.duration_seconds,
            "video_score": video.video_score,
        },
        "top_wins": [_format_insight(i) for i in wins],
        "top_improvements": [_format_insight(i) for i in improvements],
        "next_post_ideas": [_format_insight(i) for i in next_post_ideas],
        "creative_tweaks": [_format_insight(i) for i in creative_tweaks],
        "engagement_summary": {
            "views": engagement.views if engagement else None,
            "avg_retention_pct": engagement.avg_view_percentage if engagement else None,
            "best_segment": _format_segment_brief(best_segment) if best_segment else None,
            "worst_segment": _format_segment_brief(worst_segment) if worst_segment else None,
        },
        "script_analysis": analysis_sections.get("script_analysis"),
        "delivery_analysis": analysis_sections.get("delivery_analysis"),
        "visual_analysis": analysis_sections.get("visual_analysis"),
        "audience_insights": analysis_sections.get("audience_insights"),
        "processing_status": video.processing_status,
    }


def _format_insight(insight: Insight) -> dict:
    return {
        "id": str(insight.id),
        "type": insight.insight_type,
        "category": insight.category,
        "title": insight.title,
        "description": insight.description,
        "priority_rank": insight.priority_rank,
        "confidence": insight.confidence,
        "creator_match": insight.creator_match,
        "creator_match_note": insight.creator_match_note,
    }


def _format_segment_brief(segment: VideoSegment) -> dict:
    return {
        "segment_index": segment.segment_index,
        "start_ms": segment.start_ms,
        "end_ms": segment.end_ms,
        "segment_type": segment.segment_type,
        "avg_retention": segment.engagement.avg_retention if segment.engagement else None,
    }
