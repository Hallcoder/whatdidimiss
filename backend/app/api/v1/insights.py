from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db
from app.models.channel import Channel
from app.models.insight import Insight
from app.models.user import User
from app.models.video import Video
from app.utils.exceptions import NotFoundError

router = APIRouter(prefix="/videos/{video_id}/insights", tags=["insights"])


@router.get("")
async def get_insights(
    video_id: uuid.UUID,
    type: str | None = Query(None, description="Filter by insight type: win, improvement, next_post, creative_tweak"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify video belongs to user
    video_result = await db.execute(
        select(Video).join(Channel).where(Video.id == video_id, Channel.user_id == current_user.id)
    )
    if not video_result.scalar_one_or_none():
        raise NotFoundError(message=f"Video {video_id} not found")

    query = (
        select(Insight)
        .options(selectinload(Insight.segments))
        .where(Insight.video_id == video_id)
    )
    if type:
        query = query.where(Insight.insight_type == type)
    query = query.order_by(Insight.priority_rank)

    result = await db.execute(query)
    insights = result.scalars().all()

    return {
        "items": [
            {
                "id": str(i.id),
                "type": i.insight_type,
                "category": i.category,
                "title": i.title,
                "description": i.description,
                "priority_rank": i.priority_rank,
                "confidence": i.confidence,
                "referenced_segments": [
                    {
                        "segment_id": str(s.id),
                        "start_ms": s.start_ms,
                        "end_ms": s.end_ms,
                        "transcript_snippet": (s.transcript_text[:200] if s.transcript_text else None),
                    }
                    for s in i.segments
                ],
            }
            for i in insights
        ]
    }
