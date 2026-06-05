from __future__ import annotations

from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class VideoAnalysis(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "video_analyses"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    labels: Mapped[Optional[dict]] = mapped_column(JSON)
    shot_changes: Mapped[Optional[dict]] = mapped_column(JSON)
    text_detections: Mapped[Optional[dict]] = mapped_column(JSON)
    transcript: Mapped[Optional[dict]] = mapped_column(JSON)
    face_detections: Mapped[Optional[dict]] = mapped_column(JSON)
    raw_response: Mapped[Optional[dict]] = mapped_column(JSON)
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
    )

    video = relationship("Video", back_populates="analysis")
