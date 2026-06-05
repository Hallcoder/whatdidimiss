from __future__ import annotations

import re
import tempfile
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import logging

from app.models.channel import Channel
from app.models.video import Video
from app.utils.exceptions import ConflictError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

YOUTUBE_URL_PATTERNS = [
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})",
]

ALLOWED_VIDEO_TYPES = {
    "video/mp4",
    "video/quicktime",     # .mov
    "video/webm",
}
MAX_UPLOAD_SIZE_MB = 500


def extract_video_id(url: str) -> str | None:
    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


class VideoIngestService:
    async def validate_and_create(
        self,
        youtube_url: str,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> Video:
        video_id = extract_video_id(youtube_url)
        if not video_id:
            raise ValidationError(message="Invalid YouTube URL")

        # Check if video already exists
        existing = await db.execute(
            select(Video).where(Video.youtube_video_id == video_id)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(message="This video has already been submitted for analysis")

        # Verify user has at least one channel (will be populated during OAuth)
        channel_result = await db.execute(
            select(Channel).where(Channel.user_id == user_id).limit(1)
        )
        channel = channel_result.scalar_one_or_none()
        if not channel:
            raise NotFoundError(
                message="No YouTube channel linked. Please re-authenticate to link your channel."
            )

        video = Video(
            channel_id=channel.id,
            youtube_video_id=video_id,
            processing_status="pending",
        )
        db.add(video)
        await db.flush()

        # Enqueue the processing pipeline
        try:
            from app.workers.video_tasks import enqueue_video_pipeline
            enqueue_video_pipeline(str(video.id))
        except Exception:
            logger.warning("Could not enqueue pipeline (Redis unavailable?). Video saved with pending status.")

        return video

    async def create_from_upload(
        self,
        file: UploadFile,
        user_id: uuid.UUID,
        db: AsyncSession,
        title: str | None = None,
    ) -> Video:
        """Create a Video record from a direct file upload, upload to GCS, and enqueue the pipeline."""
        # Validate file type
        content_type = file.content_type or ""
        if content_type not in ALLOWED_VIDEO_TYPES:
            raise ValidationError(
                message=f"Unsupported file type: {content_type}. Allowed: mp4, mov, webm."
            )

        # Verify user has at least one channel
        channel_result = await db.execute(
            select(Channel).where(Channel.user_id == user_id).limit(1)
        )
        channel = channel_result.scalar_one_or_none()
        if not channel:
            raise NotFoundError(
                message="No YouTube channel linked. Please re-authenticate to link your channel."
            )

        # Save to temp file and upload to GCS
        tmp_dir = tempfile.mkdtemp(prefix="wdim_upload_")
        ext = _extension_from_content_type(content_type)
        video_db_id = uuid.uuid4()
        tmp_path = Path(tmp_dir) / f"{video_db_id}{ext}"

        try:
            contents = await file.read()
            size_mb = len(contents) / (1024 * 1024)
            if size_mb > MAX_UPLOAD_SIZE_MB:
                raise ValidationError(
                    message=f"File too large ({size_mb:.0f} MB). Max is {MAX_UPLOAD_SIZE_MB} MB."
                )

            tmp_path.write_bytes(contents)

            from app.services.gcs_service import GCSService

            gcs_service = GCSService()
            destination_blob = f"videos/{video_db_id}/upload{ext}"
            gcs_uri = gcs_service.upload_file(tmp_path, destination_blob)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
            try:
                tmp_path.parent.rmdir()
            except Exception:
                pass

        video = Video(
            id=video_db_id,
            channel_id=channel.id,
            youtube_video_id=None,
            title=title or file.filename or "Uploaded Video",
            processing_status="pending",
            gcs_uri=gcs_uri,
        )
        db.add(video)
        await db.flush()

        # Enqueue upload pipeline (skips ingest — video is already in GCS)
        try:
            from app.workers.video_tasks import enqueue_upload_pipeline
            enqueue_upload_pipeline(str(video.id))
        except Exception:
            logger.warning("Could not enqueue upload pipeline (Redis unavailable?). Video saved with pending status.")

        return video


def _extension_from_content_type(content_type: str) -> str:
    mapping = {
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "video/webm": ".webm",
    }
    return mapping.get(content_type, ".mp4")
