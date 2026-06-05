from __future__ import annotations

from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Channel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "channels"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    youtube_channel_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    channel_title: Mapped[Optional[str]] = mapped_column(String(255))
    subscriber_count: Mapped[Optional[int]] = mapped_column(Integer)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user = relationship("User", back_populates="channels")
    videos = relationship("Video", back_populates="channel", cascade="all, delete-orphan")
