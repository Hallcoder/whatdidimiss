from __future__ import annotations

from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SelfAssessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "self_assessments"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    hook_score: Mapped[Optional[int]] = mapped_column(Integer)
    structure_score: Mapped[Optional[int]] = mapped_column(Integer)
    clarity_score: Mapped[Optional[int]] = mapped_column(Integer)
    cta_score: Mapped[Optional[int]] = mapped_column(Integer)
    energy_score: Mapped[Optional[int]] = mapped_column(Integer)
    pacing_score: Mapped[Optional[int]] = mapped_column(Integer)
    visual_score: Mapped[Optional[int]] = mapped_column(Integer)
    best_part: Mapped[Optional[str]] = mapped_column(Text)
    would_change: Mapped[Optional[str]] = mapped_column(Text)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    video = relationship("Video", back_populates="self_assessment")
