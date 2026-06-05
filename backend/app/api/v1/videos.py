from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.channel import Channel
from app.models.user import User
from app.models.video import Video
from app.schemas.common import PaginatedResponse
from app.schemas.video import (
    ChannelVideosResponse,
    SelfAssessmentRequest,
    SelfAssessmentResponse,
    VideoAnalyzeRequest,
    VideoAnalyzeResponse,
    VideoDetailResponse,
    VideoStatusResponse,
    VideoUploadResponse,
)

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/analyze", status_code=202, response_model=VideoAnalyzeResponse)
async def analyze_video(
    body: VideoAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.video_ingest_service import VideoIngestService

    service = VideoIngestService()
    video = await service.validate_and_create(
        youtube_url=str(body.youtube_url),
        user_id=current_user.id,
        db=db,
    )
    return VideoAnalyzeResponse(
        video_id=str(video.id),
        status=video.processing_status,
        status_url=f"/api/v1/videos/{video.id}/status",
    )


@router.get("", response_model=PaginatedResponse)
async def list_videos(
    channel_id: uuid.UUID | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Video)
        .join(Channel)
        .where(Channel.user_id == current_user.id)
    )
    count_query = (
        select(func.count())
        .select_from(Video)
        .join(Channel)
        .where(Channel.user_id == current_user.id)
    )

    if channel_id:
        query = query.where(Video.channel_id == channel_id)
        count_query = count_query.where(Video.channel_id == channel_id)
    if status:
        query = query.where(Video.processing_status == status)
        count_query = count_query.where(Video.processing_status == status)

    total = (await db.execute(count_query)).scalar_one()
    query = query.order_by(Video.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    videos = result.scalars().all()

    return PaginatedResponse(
        items=[_video_summary(v) for v in videos],
        page=page,
        per_page=per_page,
        total=total,
        total_pages=(total + per_page - 1) // per_page,
    )


@router.post("/upload", status_code=202, response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.video_ingest_service import VideoIngestService

    service = VideoIngestService()
    video = await service.create_from_upload(
        file=file,
        title=title,
        user_id=current_user.id,
        db=db,
    )
    return VideoUploadResponse(
        video_id=str(video.id),
        status=video.processing_status,
        status_url=f"/api/v1/videos/{video.id}/status",
    )


@router.get("/channel-videos", response_model=ChannelVideosResponse)
async def list_channel_videos(
    page_token: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.config import settings
    from app.services.auth_service import AuthService
    from app.services.youtube_data_service import YouTubeDataService
    from app.utils.exceptions import NotFoundError, ValidationError

    if settings.auth_disabled:
        raise ValidationError(message="Channel browsing requires YouTube authentication")

    channel_result = await db.execute(
        select(Channel).where(Channel.user_id == current_user.id).limit(1)
    )
    channel = channel_result.scalar_one_or_none()
    if not channel:
        raise NotFoundError(message="No YouTube channel linked. Please re-authenticate.")

    from google.oauth2.credentials import Credentials

    auth_service = AuthService()
    creds = Credentials(
        token=auth_service._decrypt(current_user.access_token),
        refresh_token=auth_service._decrypt(current_user.refresh_token),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    )

    yt_service = YouTubeDataService()
    page = yt_service.fetch_channel_videos(
        channel_id=channel.youtube_channel_id,
        credentials=creds,
        page_token=page_token,
    )

    yt_ids = [v.youtube_video_id for v in page.items]
    analyzed_result = await db.execute(
        select(Video.youtube_video_id).where(Video.youtube_video_id.in_(yt_ids))
    )
    analyzed_ids = set(analyzed_result.scalars().all())

    from app.schemas.video import ChannelVideoItem as ChannelVideoSchema

    items = [
        ChannelVideoSchema(
            youtube_video_id=v.youtube_video_id,
            title=v.title,
            thumbnail_url=v.thumbnail_url,
            duration_seconds=v.duration_seconds,
            published_at=v.published_at,
            view_count=v.view_count,
            already_analyzed=v.youtube_video_id in analyzed_ids,
        )
        for v in page.items
    ]

    return ChannelVideosResponse(
        items=items,
        next_page_token=page.next_page_token,
        total_results=page.total_results,
    )


@router.post("/{video_id}/reanalyze", status_code=202, response_model=VideoAnalyzeResponse)
async def reanalyze_video(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.engagement_data import EngagementSnapshot, VideoSegment
    from app.models.insight import Insight
    from app.models.self_assessment import SelfAssessment
    from app.models.video_analysis import VideoAnalysis
    from app.utils.exceptions import NotFoundError

    result = await db.execute(
        select(Video).join(Channel).where(Video.id == video_id, Channel.user_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise NotFoundError(message=f"Video {video_id} not found")

    # Delete existing analysis data
    for model in [Insight, VideoSegment, EngagementSnapshot, VideoAnalysis, SelfAssessment]:
        existing = await db.execute(select(model).where(model.video_id == video_id))
        for row in existing.scalars().all():
            await db.delete(row)

    # Reset video status
    video.processing_status = "pending"
    video.processing_error = None
    video.video_score = None
    await db.flush()

    # Enqueue appropriate pipeline
    try:
        if video.youtube_video_id:
            from app.workers.video_tasks import enqueue_video_pipeline
            enqueue_video_pipeline(str(video.id))
        else:
            from app.workers.video_tasks import enqueue_upload_pipeline
            enqueue_upload_pipeline(str(video.id))
    except Exception:
        pass

    return VideoAnalyzeResponse(
        video_id=str(video.id),
        status=video.processing_status,
        status_url=f"/api/v1/videos/{video.id}/status",
    )


@router.post("/{video_id}/self-assessment", response_model=SelfAssessmentResponse)
async def submit_self_assessment(
    video_id: uuid.UUID,
    body: SelfAssessmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone

    from app.models.self_assessment import SelfAssessment
    from app.utils.exceptions import NotFoundError

    result = await db.execute(
        select(Video).join(Channel).where(Video.id == video_id, Channel.user_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise NotFoundError(message=f"Video {video_id} not found")

    # Upsert
    existing = await db.execute(
        select(SelfAssessment).where(SelfAssessment.video_id == video_id)
    )
    assessment = existing.scalar_one_or_none()

    if assessment:
        for field in [
            "hook_score", "structure_score", "clarity_score", "cta_score",
            "energy_score", "pacing_score", "visual_score", "best_part", "would_change",
        ]:
            setattr(assessment, field, getattr(body, field))
        assessment.submitted_at = datetime.now(timezone.utc)
    else:
        assessment = SelfAssessment(
            video_id=video_id,
            **body.model_dump(),
            submitted_at=datetime.now(timezone.utc),
        )
        db.add(assessment)

    await db.flush()

    return SelfAssessmentResponse(
        hook_score=assessment.hook_score,
        structure_score=assessment.structure_score,
        clarity_score=assessment.clarity_score,
        cta_score=assessment.cta_score,
        energy_score=assessment.energy_score,
        pacing_score=assessment.pacing_score,
        visual_score=assessment.visual_score,
        best_part=assessment.best_part,
        would_change=assessment.would_change,
        submitted_at=assessment.submitted_at.isoformat() if assessment.submitted_at else None,
    )


@router.get("/{video_id}/self-assessment", response_model=SelfAssessmentResponse)
async def get_self_assessment(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.self_assessment import SelfAssessment
    from app.utils.exceptions import NotFoundError

    result = await db.execute(
        select(Video).join(Channel).where(Video.id == video_id, Channel.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundError(message=f"Video {video_id} not found")

    existing = await db.execute(
        select(SelfAssessment).where(SelfAssessment.video_id == video_id)
    )
    assessment = existing.scalar_one_or_none()
    if not assessment:
        raise NotFoundError(message="No self-assessment submitted for this video")

    return SelfAssessmentResponse(
        hook_score=assessment.hook_score,
        structure_score=assessment.structure_score,
        clarity_score=assessment.clarity_score,
        cta_score=assessment.cta_score,
        energy_score=assessment.energy_score,
        pacing_score=assessment.pacing_score,
        visual_score=assessment.visual_score,
        best_part=assessment.best_part,
        would_change=assessment.would_change,
        submitted_at=assessment.submitted_at.isoformat() if assessment.submitted_at else None,
    )


@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.utils.exceptions import NotFoundError

    result = await db.execute(
        select(Video).join(Channel).where(Video.id == video_id, Channel.user_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise NotFoundError(message=f"Video {video_id} not found")

    return VideoDetailResponse(
        id=str(video.id),
        youtube_video_id=video.youtube_video_id,
        title=video.title,
        description=video.description,
        duration_seconds=video.duration_seconds,
        thumbnail_url=video.thumbnail_url,
        processing_status=video.processing_status,
        processing_error=video.processing_error,
        created_at=video.created_at.isoformat(),
    )


@router.delete("/{video_id}", status_code=204)
async def delete_video(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.utils.exceptions import NotFoundError

    result = await db.execute(
        select(Video).join(Channel).where(Video.id == video_id, Channel.user_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise NotFoundError(message=f"Video {video_id} not found")

    await db.delete(video)
    return None


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.utils.exceptions import NotFoundError

    result = await db.execute(
        select(Video).join(Channel).where(Video.id == video_id, Channel.user_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise NotFoundError(message=f"Video {video_id} not found")

    all_steps = [
        "pending", "downloading", "uploading_gcs",
        "analyzing_video", "fetching_analytics", "correlating", "synthesizing", "completed",
    ]
    current_idx = all_steps.index(video.processing_status) if video.processing_status in all_steps else 0
    steps_completed = all_steps[:current_idx]
    steps_remaining = all_steps[current_idx + 1:] if video.processing_status != "completed" else []

    return VideoStatusResponse(
        status=video.processing_status,
        progress_pct=int((current_idx / (len(all_steps) - 1)) * 100),
        current_step=video.processing_status,
        steps_completed=steps_completed,
        steps_remaining=steps_remaining,
        error=video.processing_error,
    )


def _video_summary(video: Video) -> dict:
    return {
        "id": str(video.id),
        "youtube_video_id": video.youtube_video_id,
        "title": video.title,
        "thumbnail_url": video.thumbnail_url,
        "duration_seconds": video.duration_seconds,
        "processing_status": video.processing_status,
        "video_score": video.video_score,
        "created_at": video.created_at.isoformat(),
    }
