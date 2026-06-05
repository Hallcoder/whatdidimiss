from __future__ import annotations

from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class EngagementSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "engagement_snapshots"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    views: Mapped[Optional[int]] = mapped_column(Integer)
    likes: Mapped[Optional[int]] = mapped_column(Integer)
    dislikes: Mapped[Optional[int]] = mapped_column(Integer)
    comments: Mapped[Optional[int]] = mapped_column(Integer)
    shares: Mapped[Optional[int]] = mapped_column(Integer)
    avg_view_duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    avg_view_percentage: Mapped[Optional[float]] = mapped_column(Float)
    retention_curve: Mapped[Optional[dict]] = mapped_column(JSON)
    traffic_sources: Mapped[Optional[dict]] = mapped_column(JSON)
    demographics: Mapped[Optional[dict]] = mapped_column(JSON)
    top_geographies: Mapped[Optional[dict]] = mapped_column(JSON)
    top_comments: Mapped[Optional[dict]] = mapped_column(JSON)
    fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    video = relationship("Video", back_populates="engagement_snapshot")


class VideoSegment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "video_segments"
    __table_args__ = (
        UniqueConstraint("video_id", "segment_index", name="uq_video_segment_index"),
    )

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    segment_type: Mapped[Optional[str]] = mapped_column(String(50))
    labels: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))
    transcript_text: Mapped[Optional[str]] = mapped_column(Text)
    pacing_score: Mapped[Optional[float]] = mapped_column(Float)

    video = relationship("Video", back_populates="segments")
    engagement = relationship(
        "SegmentEngagement", back_populates="segment", uselist=False, cascade="all, delete-orphan"
    )
    insights = relationship("Insight", secondary="insight_segments", back_populates="segments")


class SegmentEngagement(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "segment_engagement"

    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("video_segments.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    avg_retention: Mapped[Optional[float]] = mapped_column(Float)
    retention_delta: Mapped[Optional[float]] = mapped_column(Float)
    relative_performance: Mapped[Optional[float]] = mapped_column(Float)
    engagement_label: Mapped[Optional[str]] = mapped_column(String(50))

    segment = relationship("VideoSegment", back_populates="engagement")
