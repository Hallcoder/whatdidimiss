from __future__ import annotations

import logging
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog
from celery import chain
from sqlalchemy import select

from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


def enqueue_video_pipeline(video_id: str):
    """Enqueue the full video analysis pipeline as a Celery chain."""
    pipeline = chain(
        video_ingest_task.s(video_id),
        video_analysis_task.s(),
        analytics_fetch_task.s(),
        correlation_task.s(),
        synthesis_task.s(),
    )
    pipeline.apply_async()


def enqueue_upload_pipeline(video_id: str):
    """Enqueue the pipeline for an uploaded video (already in GCS, skip ingest + analytics)."""
    pipeline = chain(
        video_analysis_task.s(video_id),
        upload_analytics_stub_task.s(),
        correlation_task.s(),
        synthesis_task.s(),
    )
    pipeline.apply_async()


def _get_sync_session():
    """Create a synchronous DB session for use in Celery workers."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

    from app.config import settings

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _update_video_status(session, video_id: str, status: str, **extra_fields):
    """Update video processing status and any extra fields."""
    from app.models.video import Video

    video = session.execute(
        select(Video).where(Video.id == uuid.UUID(video_id))
    ).scalar_one()
    video.processing_status = status
    for field, value in extra_fields.items():
        setattr(video, field, value)
    session.commit()
    return video


def _safe_retry(task, exc, video_id: str):
    """Retry a task or mark the video as permanently failed if retries are exhausted."""
    if task.request.retries >= task.max_retries:
        logger.error(
            "task_retries_exhausted",
            task=task.name,
            video_id=video_id,
            retries=task.request.retries,
        )
        session = _get_sync_session()
        try:
            _update_video_status(
                session, video_id, "failed",
                processing_error=f"Permanently failed after {task.max_retries} retries: {exc}",
            )
        except Exception:
            logger.exception("failed_to_mark_video_failed", video_id=video_id)
        finally:
            session.close()
        raise exc  # Re-raise to stop the chain
    raise task.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def video_ingest_task(self, video_id: str) -> str:
    """Step 1: Fetch metadata, download video via yt-dlp, upload to GCS."""
    session = _get_sync_session()
    tmp_path = None

    try:
        from app.models.channel import Channel
        from app.models.video import Video
        from app.services.auth_service import AuthService
        from app.services.gcs_service import GCSService
        from app.services.youtube_data_service import YouTubeDataService

        # Load video and channel
        video = session.execute(
            select(Video).where(Video.id == uuid.UUID(video_id))
        ).scalar_one()
        channel = session.execute(
            select(Channel).where(Channel.id == video.channel_id)
        ).scalar_one()

        # --- Phase 1: Fetch metadata ---
        _update_video_status(session, video_id, "downloading")
        logger.info("Fetching metadata for video %s (yt:%s)", video_id, video.youtube_video_id)

        from app.config import settings

        # Try YouTube Data API if user has real credentials, otherwise use yt-dlp metadata
        metadata_fetched = False
        if not settings.auth_disabled:
            try:
                from google.oauth2.credentials import Credentials
                from app.models.user import User

                auth_service = AuthService()
                user = session.execute(
                    select(User).where(User.id == channel.user_id)
                ).scalar_one()

                creds = Credentials(
                    token=auth_service._decrypt(user.access_token),
                    refresh_token=auth_service._decrypt(user.refresh_token),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=settings.google_client_id,
                    client_secret=settings.google_client_secret,
                )

                yt_service = YouTubeDataService()
                metadata = yt_service.fetch_video_metadata(video.youtube_video_id, creds)

                video.title = metadata.title
                video.description = metadata.description
                video.published_at = datetime.fromisoformat(metadata.published_at.replace("Z", "+00:00"))
                video.duration_seconds = metadata.duration_seconds
                video.thumbnail_url = metadata.thumbnail_url
                session.commit()
                metadata_fetched = True
                logger.info("Metadata fetched via API: '%s' (%ds)", metadata.title, metadata.duration_seconds)
            except Exception as e:
                logger.warning("YouTube Data API metadata fetch failed: %s", e)

        if not metadata_fetched:
            # Fallback: get metadata from yt-dlp
            logger.info("Fetching metadata via yt-dlp for %s", video.youtube_video_id)
            meta = _get_ytdlp_metadata(video.youtube_video_id)
            video.title = meta.get("title", "Untitled")
            video.description = meta.get("description", "")
            video.duration_seconds = meta.get("duration")
            video.thumbnail_url = meta.get("thumbnail")
            session.commit()
            logger.info("Metadata via yt-dlp: '%s' (%ss)", video.title, video.duration_seconds)

        # --- Phase 2: Download video via yt-dlp ---
        logger.info("Downloading video %s via yt-dlp", video.youtube_video_id)

        tmp_dir = tempfile.mkdtemp(prefix="wdim_")
        tmp_path = Path(tmp_dir) / f"{video.youtube_video_id}.mp4"

        _download_video(video.youtube_video_id, tmp_path)

        if not tmp_path.exists():
            raise RuntimeError(f"yt-dlp did not produce output file at {tmp_path}")

        file_size_mb = tmp_path.stat().st_size / (1024 * 1024)
        logger.info("Downloaded video: %.1f MB", file_size_mb)

        # --- Phase 3: Upload to GCS ---
        _update_video_status(session, video_id, "uploading_gcs")
        logger.info("Uploading video to GCS")

        gcs_service = GCSService()
        destination_blob = f"videos/{video_id}/{video.youtube_video_id}.mp4"
        gcs_uri = gcs_service.upload_file(tmp_path, destination_blob)

        video = session.execute(
            select(Video).where(Video.id == uuid.UUID(video_id))
        ).scalar_one()
        video.gcs_uri = gcs_uri
        session.commit()

        logger.info("GCS URI set to %s", gcs_uri)

        return video_id

    except Exception as exc:
        session.rollback()
        try:
            _update_video_status(session, video_id, "failed", processing_error=str(exc))
        except Exception:
            logger.exception("Failed to update video status after error")
        logger.exception("video_ingest_task failed for %s", video_id)
        _safe_retry(self, exc, video_id)

    finally:
        # Clean up temp file
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
                tmp_path.parent.rmdir()
            except Exception:
                pass
        session.close()


def _get_ytdlp_opts() -> dict:
    """Base yt-dlp options with cookie support for dev."""
    from app.config import settings

    opts: dict = {"quiet": True, "no_warnings": True}
    if settings.ytdlp_cookies_file:
        opts["cookiefile"] = settings.ytdlp_cookies_file
    return opts


def _get_ytdlp_metadata(youtube_video_id: str) -> dict:
    """Fetch video metadata using yt-dlp without downloading."""
    import yt_dlp

    url = f"https://www.youtube.com/watch?v={youtube_video_id}"
    ydl_opts = {**_get_ytdlp_opts(), "skip_download": True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title"),
            "description": info.get("description", ""),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
        }


def _download_video(youtube_video_id: str, output_path: Path, oauth_token: str = None) -> None:
    """Download a YouTube video using yt-dlp."""
    import yt_dlp

    ydl_opts = {
        **_get_ytdlp_opts(),
        "format": "best",
        "outtmpl": str(output_path),
        "socket_timeout": 30,
        "retries": 3,
    }

    url = f"https://www.youtube.com/watch?v={youtube_video_id}"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def video_analysis_task(self, video_id: str) -> str:
    """Step 2: Run Google Video Intelligence API analysis."""
    from datetime import datetime as dt
    from datetime import timezone as tz

    from app.models.engagement_data import VideoSegment
    from app.models.video import Video
    from app.models.video_analysis import VideoAnalysis
    from app.services.segment_service import derive_segments
    from app.services.video_intelligence_service import VideoIntelligenceService

    session = _get_sync_session()
    try:
        _update_video_status(session, video_id, "analyzing_video")

        video = session.execute(
            select(Video).where(Video.id == uuid.UUID(video_id))
        ).scalar_one()

        if not video.gcs_uri:
            raise RuntimeError(f"Video {video_id} has no GCS URI — ingest may have failed")

        # Run Video Intelligence API
        vi_service = VideoIntelligenceService()
        vi_result = vi_service.analyze_video(video.gcs_uri)

        logger.info(
            "Video Intelligence results: %d labels, %d shots, %d text, %d transcript segments",
            len(vi_result.labels),
            len(vi_result.shot_changes),
            len(vi_result.text_detections),
            len(vi_result.transcript),
        )

        # If no transcript from Video Intelligence, try YouTube captions (only for YouTube videos)
        transcript_data = vi_result.raw_response.get("transcript")
        if not vi_result.transcript and video.youtube_video_id:
            logger.info("No transcript from Video Intelligence, fetching YouTube captions")
            from app.services.youtube_captions_service import YouTubeCaptionsService
            from app.models.channel import Channel
            from app.models.user import User
            from app.services.auth_service import AuthService
            from google.oauth2.credentials import Credentials
            from app.config import settings

            try:
                channel = session.execute(
                    select(Channel).where(Channel.id == video.channel_id)
                ).scalar_one()
                user = session.execute(
                    select(User).where(User.id == channel.user_id)
                ).scalar_one()

                auth_service = AuthService()
                creds = Credentials(
                    token=auth_service._decrypt(user.access_token),
                    refresh_token=auth_service._decrypt(user.refresh_token),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=settings.google_client_id,
                    client_secret=settings.google_client_secret,
                )

                captions_service = YouTubeCaptionsService()
                yt_transcript = captions_service.fetch_transcript(video.youtube_video_id, creds)
                if yt_transcript:
                    transcript_data = yt_transcript
                    # Inject into vi_result so segment derivation can use it
                    from app.services.video_intelligence_service import TranscriptSegment
                    vi_result.transcript = [
                        TranscriptSegment(
                            text=seg["text"],
                            confidence=seg.get("confidence", 1.0),
                            start_ms=seg["start_ms"],
                            end_ms=seg["end_ms"],
                            words=[],
                        )
                        for seg in yt_transcript
                    ]
                    logger.info("YouTube captions: %d segments fetched", len(yt_transcript))
            except Exception as e:
                logger.warning("Failed to fetch YouTube captions: %s", e)

        # Store raw analysis
        analysis = VideoAnalysis(
            video_id=video.id,
            labels=vi_result.raw_response.get("labels"),
            shot_changes=vi_result.raw_response.get("shot_changes"),
            text_detections=vi_result.raw_response.get("text_detections"),
            transcript=transcript_data,
            raw_response=vi_result.raw_response,
            analyzed_at=dt.now(tz.utc),
        )
        session.add(analysis)

        # Derive segments
        duration_ms = (video.duration_seconds or 0) * 1000
        segment_dicts = derive_segments(vi_result, duration_ms)

        logger.info("Derived %d segments from video analysis", len(segment_dicts))

        for seg_dict in segment_dicts:
            segment = VideoSegment(
                video_id=video.id,
                segment_index=seg_dict["segment_index"],
                start_ms=seg_dict["start_ms"],
                end_ms=seg_dict["end_ms"],
                segment_type=seg_dict["segment_type"],
                labels=seg_dict["labels"],
                transcript_text=seg_dict["transcript_text"],
                pacing_score=seg_dict["pacing_score"],
            )
            session.add(segment)

        session.commit()
        return video_id

    except Exception as exc:
        session.rollback()
        try:
            _update_video_status(session, video_id, "failed", processing_error=str(exc))
        except Exception:
            pass
        logger.exception("video_analysis_task failed for %s", video_id)
        _safe_retry(self, exc, video_id)
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def analytics_fetch_task(self, video_id: str) -> str:
    """Step 3: Fetch YouTube Analytics data."""
    from datetime import datetime as dt
    from datetime import timezone as tz

    from app.config import settings
    from app.models.engagement_data import EngagementSnapshot
    from app.models.video import Video

    session = _get_sync_session()
    try:
        _update_video_status(session, video_id, "fetching_analytics")

        # Skip analytics fetch when auth is disabled (no real YouTube tokens)
        if settings.auth_disabled:
            logger.info("Auth disabled — skipping YouTube Analytics for %s", video_id)
            video = session.execute(
                select(Video).where(Video.id == uuid.UUID(video_id))
            ).scalar_one()
            snapshot = EngagementSnapshot(
                video_id=video.id,
                views=0,
                likes=0,
                comments=0,
                fetched_at=dt.now(tz.utc),
            )
            session.add(snapshot)
            session.commit()
            return video_id

        from google.oauth2.credentials import Credentials

        from app.models.channel import Channel
        from app.models.user import User
        from app.services.auth_service import AuthService
        from app.services.youtube_analytics_service import YouTubeAnalyticsService

        video = session.execute(
            select(Video).where(Video.id == uuid.UUID(video_id))
        ).scalar_one()
        channel = session.execute(
            select(Channel).where(Channel.id == video.channel_id)
        ).scalar_one()
        user = session.execute(
            select(User).where(User.id == channel.user_id)
        ).scalar_one()

        auth_service = AuthService()
        creds = Credentials(
            token=auth_service._decrypt(user.access_token),
            refresh_token=auth_service._decrypt(user.refresh_token),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )

        analytics_service = YouTubeAnalyticsService()
        data = analytics_service.fetch_all(
            youtube_video_id=video.youtube_video_id,
            channel_id=channel.youtube_channel_id,
            credentials=creds,
        )

        logger.info(
            "Analytics fetched: %s views, %d retention points, %d traffic sources",
            data.views,
            len(data.retention_curve),
            len(data.traffic_sources),
        )

        # Serialize retention curve for JSONB storage
        retention_json = [
            {
                "elapsed_ratio": p.elapsed_ratio,
                "watch_ratio": p.audience_watch_ratio,
                "relative_retention": p.relative_retention,
            }
            for p in data.retention_curve
        ]

        snapshot = EngagementSnapshot(
            video_id=video.id,
            views=data.views,
            likes=data.likes,
            dislikes=data.dislikes,
            comments=data.comments,
            shares=data.shares,
            avg_view_duration_seconds=data.avg_view_duration_seconds,
            avg_view_percentage=data.avg_view_percentage,
            retention_curve=retention_json,
            traffic_sources=data.traffic_sources,
            demographics=data.demographics,
            top_geographies=data.top_geographies,
            top_comments=data.top_comments,
            fetched_at=dt.now(tz.utc),
        )
        session.add(snapshot)
        session.commit()

        return video_id

    except Exception as exc:
        session.rollback()
        try:
            _update_video_status(session, video_id, "failed", processing_error=str(exc))
        except Exception:
            pass
        logger.exception("analytics_fetch_task failed for %s", video_id)
        _safe_retry(self, exc, video_id)
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=0)
def upload_analytics_stub_task(self, video_id: str) -> str:
    """Create an empty EngagementSnapshot for uploaded videos (no YouTube analytics available)."""
    from datetime import datetime as dt
    from datetime import timezone as tz

    from app.models.engagement_data import EngagementSnapshot
    from app.models.video import Video

    session = _get_sync_session()
    try:
        _update_video_status(session, video_id, "fetching_analytics")
        logger.info("Uploaded video %s — creating empty engagement snapshot", video_id)

        video = session.execute(
            select(Video).where(Video.id == uuid.UUID(video_id))
        ).scalar_one()

        snapshot = EngagementSnapshot(
            video_id=video.id,
            views=0,
            likes=0,
            comments=0,
            fetched_at=dt.now(tz.utc),
        )
        session.add(snapshot)
        session.commit()
        return video_id

    except Exception as exc:
        session.rollback()
        try:
            _update_video_status(session, video_id, "failed", processing_error=str(exc))
        except Exception:
            pass
        logger.exception("upload_analytics_stub_task failed for %s", video_id)
        raise exc
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=1, default_retry_delay=10)
def correlation_task(self, video_id: str) -> str:
    """Step 4: Correlate engagement data with video segments."""
    from app.models.engagement_data import EngagementSnapshot, SegmentEngagement, VideoSegment
    from app.models.video import Video
    from app.services.engagement_correlation_service import EngagementCorrelationService
    from app.services.youtube_analytics_service import RetentionPoint

    session = _get_sync_session()
    try:
        _update_video_status(session, video_id, "correlating")

        video = session.execute(
            select(Video).where(Video.id == uuid.UUID(video_id))
        ).scalar_one()

        # Load engagement snapshot
        snapshot = session.execute(
            select(EngagementSnapshot).where(EngagementSnapshot.video_id == video.id)
        ).scalar_one_or_none()

        if not snapshot or not snapshot.retention_curve:
            logger.warning("No retention data for video %s, skipping correlation", video_id)
            return video_id

        # Load segments
        segments_result = session.execute(
            select(VideoSegment)
            .where(VideoSegment.video_id == video.id)
            .order_by(VideoSegment.segment_index)
        )
        segments = segments_result.scalars().all()

        if not segments:
            logger.warning("No segments for video %s, skipping correlation", video_id)
            return video_id

        # Reconstruct RetentionPoint objects from stored JSON
        retention_curve = [
            RetentionPoint(
                elapsed_ratio=p["elapsed_ratio"],
                audience_watch_ratio=p["watch_ratio"],
                relative_retention=p.get("relative_retention", 1.0),
            )
            for p in snapshot.retention_curve
        ]

        # Build segment dicts for the correlation service
        segment_dicts = [
            {"id": str(s.id), "start_ms": s.start_ms, "end_ms": s.end_ms}
            for s in segments
        ]

        duration_ms = (video.duration_seconds or 0) * 1000

        correlation_service = EngagementCorrelationService()
        results = correlation_service.correlate(retention_curve, segment_dicts, duration_ms)

        logger.info("Correlated engagement for %d segments", len(results))

        for result in results:
            seg_engagement = SegmentEngagement(
                segment_id=uuid.UUID(result.segment_id),
                avg_retention=result.avg_retention,
                retention_delta=result.retention_delta,
                relative_performance=result.relative_performance,
                engagement_label=result.engagement_label,
            )
            session.add(seg_engagement)

        session.commit()
        return video_id

    except Exception as exc:
        session.rollback()
        try:
            _update_video_status(session, video_id, "failed", processing_error=str(exc))
        except Exception:
            pass
        logger.exception("correlation_task failed for %s", video_id)
        _safe_retry(self, exc, video_id)
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def synthesis_task(self, video_id: str) -> str:
    """Step 5: Generate insights via GPT-4o."""
    from app.models.engagement_data import EngagementSnapshot, SegmentEngagement, VideoSegment
    from app.models.insight import Insight, insight_segments
    from app.models.video import Video
    from app.models.video_analysis import VideoAnalysis
    from app.services.synthesis_service import SynthesisService

    session = _get_sync_session()
    try:
        _update_video_status(session, video_id, "synthesizing")

        video = session.execute(
            select(Video).where(Video.id == uuid.UUID(video_id))
        ).scalar_one()

        # Load engagement snapshot
        snapshot = session.execute(
            select(EngagementSnapshot).where(EngagementSnapshot.video_id == video.id)
        ).scalar_one_or_none()

        # Load segments with engagement data
        segments_result = session.execute(
            select(VideoSegment)
            .where(VideoSegment.video_id == video.id)
            .order_by(VideoSegment.segment_index)
        )
        segments = segments_result.scalars().all()

        # Load engagement per segment
        seg_engagement_map = {}
        if segments:
            seg_ids = [s.id for s in segments]
            eng_result = session.execute(
                select(SegmentEngagement).where(SegmentEngagement.segment_id.in_(seg_ids))
            )
            for eng in eng_result.scalars().all():
                seg_engagement_map[eng.segment_id] = eng

        # Load analysis for labels
        analysis = session.execute(
            select(VideoAnalysis).where(VideoAnalysis.video_id == video.id)
        ).scalar_one_or_none()

        # Build context dicts
        video_meta = {
            "title": video.title or "Untitled",
            "description": video.description or "",
            "duration_seconds": video.duration_seconds or 0,
            "youtube_video_id": video.youtube_video_id or "",
        }

        segments_data = []
        for seg in segments:
            eng = seg_engagement_map.get(seg.id)
            segments_data.append({
                "segment_index": seg.segment_index,
                "start_ms": seg.start_ms,
                "end_ms": seg.end_ms,
                "segment_type": seg.segment_type,
                "labels": seg.labels or [],
                "transcript_text": seg.transcript_text,
                "pacing_score": seg.pacing_score,
                "avg_retention": eng.avg_retention if eng else None,
                "retention_delta": eng.retention_delta if eng else None,
                "relative_performance": eng.relative_performance if eng else None,
                "engagement_label": eng.engagement_label if eng else None,
            })

        engagement = {
            "views": snapshot.views if snapshot else None,
            "likes": snapshot.likes if snapshot else None,
            "comments": snapshot.comments if snapshot else None,
            "shares": snapshot.shares if snapshot else None,
            "avg_view_duration_seconds": snapshot.avg_view_duration_seconds if snapshot else None,
            "avg_view_percentage": snapshot.avg_view_percentage if snapshot else None,
            "traffic_sources": snapshot.traffic_sources if snapshot else {},
        }

        retention_curve = snapshot.retention_curve if snapshot else []
        top_comments = snapshot.top_comments if snapshot else []

        # Collect top labels from analysis
        top_labels = []
        if analysis and analysis.labels:
            for lbl in analysis.labels[:15]:
                if isinstance(lbl, dict):
                    top_labels.append(lbl.get("description", ""))

        # Load creator self-assessment if available
        from app.models.self_assessment import SelfAssessment

        sa_result = session.execute(
            select(SelfAssessment).where(SelfAssessment.video_id == video.id)
        )
        self_assessment = sa_result.scalar_one_or_none()
        creator_assessment = None
        if self_assessment:
            creator_assessment = {
                "hook_score": self_assessment.hook_score,
                "structure_score": self_assessment.structure_score,
                "clarity_score": self_assessment.clarity_score,
                "cta_score": self_assessment.cta_score,
                "energy_score": self_assessment.energy_score,
                "pacing_score": self_assessment.pacing_score,
                "visual_score": self_assessment.visual_score,
                "best_part": self_assessment.best_part,
                "would_change": self_assessment.would_change,
            }
            logger.info("Creator self-assessment found for video %s", video_id)

        # Call GPT-4o
        synthesis_service = SynthesisService()
        result = synthesis_service.generate_insights(
            video_meta=video_meta,
            segments=segments_data,
            engagement=engagement,
            retention_curve=retention_curve,
            labels=top_labels,
            comments=top_comments,
            creator_assessment=creator_assessment,
        )

        model_version = synthesis_service.get_model_version()
        prompt_version = synthesis_service.get_prompt_version()

        logger.info(
            "Synthesis complete: %d wins, %d improvements, %d next_post, %d tweaks",
            len(result.get("wins", [])),
            len(result.get("improvements", [])),
            len(result.get("next_post_ideas", [])),
            len(result.get("creative_tweaks", [])),
        )

        # Build a map of segment_index -> segment DB id for linking
        seg_index_to_id = {seg.segment_index: seg.id for seg in segments}

        # Store insights
        _store_insights(
            session, video.id, "win", result.get("wins", []),
            seg_index_to_id, model_version, prompt_version, result,
        )
        _store_insights(
            session, video.id, "improvement", result.get("improvements", []),
            seg_index_to_id, model_version, prompt_version, result,
        )
        _store_insights(
            session, video.id, "next_post", result.get("next_post_ideas", []),
            seg_index_to_id, model_version, prompt_version, result,
        )
        _store_insights(
            session, video.id, "creative_tweak", result.get("creative_tweaks", []),
            seg_index_to_id, model_version, prompt_version, result,
        )

        # Store analysis sections as single insight records with JSON data
        for section_key in ["script_analysis", "delivery_analysis", "visual_analysis", "audience_insights"]:
            section_data = result.get(section_key)
            if section_data:
                insight = Insight(
                    video_id=video.id,
                    insight_type=section_key,
                    category="analysis",
                    title=section_key.replace("_", " ").title(),
                    description="",
                    priority_rank=1,
                    raw_llm_response=section_data,
                    model_version=model_version,
                    prompt_version=prompt_version,
                )
                session.add(insight)

        # Compute video index score from analysis sub-scores (each 0-10)
        video.video_score = _compute_video_score(result)
        logger.info("Video score for %s: %s", video_id, video.video_score)

        session.commit()

        _update_video_status(session, video_id, "completed")
        return video_id

    except Exception as exc:
        session.rollback()
        try:
            _update_video_status(session, video_id, "failed", processing_error=str(exc))
        except Exception:
            pass
        logger.exception("synthesis_task failed for %s", video_id)
        _safe_retry(self, exc, video_id)
    finally:
        session.close()


def _store_insights(
    session,
    video_id,
    insight_type: str,
    items: list,
    seg_index_to_id: dict,
    model_version: str,
    prompt_version: str,
    raw_llm_response: dict,
):
    """Store a list of insight items and link them to segments."""
    from app.models.insight import Insight, insight_segments

    for rank, item in enumerate(items, start=1):
        creator_match_raw = item.get("creator_match")
        creator_match = creator_match_raw if creator_match_raw in (
            "predicted", "blind_spot", "over_critical", "under_critical"
        ) else None

        insight = Insight(
            video_id=video_id,
            insight_type=insight_type,
            category=item.get("category"),
            title=item.get("title", ""),
            description=item.get("description", ""),
            priority_rank=rank,
            confidence=item.get("confidence"),
            creator_match=creator_match,
            creator_match_note=item.get("creator_match_note") if creator_match else None,
            raw_llm_response=raw_llm_response,
            model_version=model_version,
            prompt_version=prompt_version,
        )
        session.add(insight)
        session.flush()  # Get the insight.id

        # Link to segments
        segment_indices = item.get("segment_indices", [])
        for idx in segment_indices:
            seg_id = seg_index_to_id.get(idx)
            if seg_id:
                session.execute(
                    insight_segments.insert().values(
                        insight_id=insight.id,
                        segment_id=seg_id,
                    )
                )


def _compute_video_score(synthesis_result: dict) -> int | None:
    """Compute a 0-100 video index score from analysis sub-scores.

    Uses the 10 sub-scores (each 0-10) from script, delivery, and visual analysis.
    Falls back to average insight confidence if analysis sections are missing.
    """
    score_keys = {
        "script_analysis": ["hook_score", "structure_score", "clarity_score", "cta_score"],
        "delivery_analysis": ["energy_score", "pacing_score", "personality_score"],
        "visual_analysis": ["composition_score", "broll_score", "text_overlay_score"],
    }

    scores: list[float] = []
    for section, keys in score_keys.items():
        section_data = synthesis_result.get(section)
        if not isinstance(section_data, dict):
            continue
        for key in keys:
            val = section_data.get(key)
            if isinstance(val, (int, float)):
                scores.append(float(val))

    if scores:
        return round((sum(scores) / len(scores)) * 10)

    # Fallback: average confidence across insights
    confidences: list[float] = []
    for group in ["wins", "improvements", "next_post_ideas", "creative_tweaks"]:
        for item in synthesis_result.get(group, []):
            c = item.get("confidence")
            if isinstance(c, (int, float)):
                confidences.append(float(c))

    if confidences:
        return round((sum(confidences) / len(confidences)) * 100)

    return None
