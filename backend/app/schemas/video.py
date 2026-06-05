from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class VideoAnalyzeRequest(BaseModel):
    youtube_url: HttpUrl


class VideoAnalyzeResponse(BaseModel):
    video_id: str
    status: str
    status_url: str


class VideoDetailResponse(BaseModel):
    id: str
    youtube_video_id: str | None = None
    title: str | None = None
    description: str | None = None
    duration_seconds: int | None = None
    thumbnail_url: str | None = None
    processing_status: str
    processing_error: str | None = None
    created_at: str


class VideoStatusResponse(BaseModel):
    status: str
    progress_pct: int
    current_step: str
    steps_completed: list[str]
    steps_remaining: list[str]
    error: str | None = None


class ChannelVideoItem(BaseModel):
    youtube_video_id: str
    title: str
    thumbnail_url: str | None = None
    duration_seconds: int
    published_at: str
    view_count: int | None = None
    already_analyzed: bool = False


class ChannelVideosResponse(BaseModel):
    items: list[ChannelVideoItem]
    next_page_token: str | None = None
    total_results: int | None = None


class VideoUploadResponse(BaseModel):
    video_id: str
    status: str
    status_url: str


class SelfAssessmentRequest(BaseModel):
    hook_score: int | None = Field(None, ge=1, le=10)
    structure_score: int | None = Field(None, ge=1, le=10)
    clarity_score: int | None = Field(None, ge=1, le=10)
    cta_score: int | None = Field(None, ge=1, le=10)
    energy_score: int | None = Field(None, ge=1, le=10)
    pacing_score: int | None = Field(None, ge=1, le=10)
    visual_score: int | None = Field(None, ge=1, le=10)
    best_part: str | None = None
    would_change: str | None = None


class SelfAssessmentResponse(BaseModel):
    hook_score: int | None = None
    structure_score: int | None = None
    clarity_score: int | None = None
    cta_score: int | None = None
    energy_score: int | None = None
    pacing_score: int | None = None
    visual_score: int | None = None
    best_part: str | None = None
    would_change: str | None = None
    submitted_at: str | None = None
