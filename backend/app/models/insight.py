from __future__ import annotations

from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

insight_segments = Table(
    "insight_segments",
    Base.metadata,
    Column("insight_id", UUID(as_uuid=True), ForeignKey("insights.id", ondelete="CASCADE"), primary_key=True),
    Column("segment_id", UUID(as_uuid=True), ForeignKey("video_segments.id", ondelete="CASCADE"), primary_key=True),
)


class Insight(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "insights"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    insight_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority_rank: Mapped[Optional[int]] = mapped_column(Integer)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    raw_llm_response: Mapped[Optional[dict]] = mapped_column(JSON)
    model_version: Mapped[Optional[str]] = mapped_column(String(50))
    prompt_version: Mapped[Optional[str]] = mapped_column(String(50))
    creator_match: Mapped[Optional[str]] = mapped_column(String(20))
    creator_match_note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    video = relationship("Video", back_populates="insights")
    segments = relationship("VideoSegment", secondary=insight_segments, back_populates="insights")
