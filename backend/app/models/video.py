from __future__ import annotations

from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Video(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "videos"

    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text)
    gcs_uri: Mapped[Optional[str]] = mapped_column(Text)
    processing_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )
    processing_error: Mapped[Optional[str]] = mapped_column(Text)
    video_score: Mapped[Optional[int]] = mapped_column(Integer)

    channel = relationship("Channel", back_populates="videos")
    analysis = relationship("VideoAnalysis", back_populates="video", uselist=False, cascade="all, delete-orphan")
    engagement_snapshot = relationship(
        "EngagementSnapshot", back_populates="video", uselist=False, cascade="all, delete-orphan"
    )
    segments = relationship("VideoSegment", back_populates="video", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="video", cascade="all, delete-orphan")
    self_assessment = relationship(
        "SelfAssessment", back_populates="video", uselist=False, cascade="all, delete-orphan"
    )
