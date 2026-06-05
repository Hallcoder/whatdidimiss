from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.utils.exceptions import YouTubeAPIError

logger = logging.getLogger(__name__)


@dataclass
class RetentionPoint:
    """One of the 100 data points YouTube returns per video."""
    elapsed_ratio: float          # 0.0 – 1.0 position through the video
    audience_watch_ratio: float   # absolute % of viewers still watching
    relative_retention: float     # performance vs similar-length videos


@dataclass
class EngagementData:
    views: Optional[int] = None
    likes: Optional[int] = None
    dislikes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    avg_view_duration_seconds: Optional[float] = None
    avg_view_percentage: Optional[float] = None
    retention_curve: list[RetentionPoint] = field(default_factory=list)
    traffic_sources: dict[str, float] = field(default_factory=dict)
    demographics: dict[str, Any] = field(default_factory=dict)
    top_geographies: list[dict] = field(default_factory=list)
    top_comments: list[dict] = field(default_factory=list)


class YouTubeAnalyticsService:
    """Fetches engagement data from YouTube Analytics API v2 and Data API v3."""

    def fetch_all(
        self,
        youtube_video_id: str,
        channel_id: str,
        credentials: Credentials,
    ) -> EngagementData:
        """Aggregate all engagement data for a single video."""
        data = EngagementData()

        # Video statistics from Data API (views, likes, comments)
        stats = self._fetch_video_statistics(youtube_video_id, credentials)
        data.views = stats.get("viewCount")
        data.likes = stats.get("likeCount")
        data.dislikes = stats.get("dislikeCount")
        data.comments = stats.get("commentCount")

        # Analytics API calls (require channel ownership)
        try:
            overview = self._fetch_analytics_overview(youtube_video_id, channel_id, credentials)
            data.avg_view_duration_seconds = overview.get("averageViewDuration")
            data.avg_view_percentage = overview.get("averageViewPercentage")
            data.shares = overview.get("shares")
        except Exception:
            logger.warning("Failed to fetch analytics overview, continuing with partial data")

        try:
            data.retention_curve = self._fetch_retention_curve(
                youtube_video_id, channel_id, credentials
            )
        except Exception:
            logger.warning("Failed to fetch retention curve, continuing with partial data")

        try:
            data.traffic_sources = self._fetch_traffic_sources(
                youtube_video_id, channel_id, credentials
            )
        except Exception:
            logger.warning("Failed to fetch traffic sources, continuing with partial data")

        try:
            data.demographics = self._fetch_demographics(
                youtube_video_id, channel_id, credentials
            )
        except Exception:
            logger.warning("Failed to fetch demographics, continuing with partial data")

        try:
            data.top_geographies = self._fetch_geographies(
                youtube_video_id, channel_id, credentials
            )
        except Exception:
            logger.warning("Failed to fetch geographies, continuing with partial data")

        try:
            data.top_comments = self._fetch_top_comments(youtube_video_id, credentials)
        except Exception:
            logger.warning("Failed to fetch comments, continuing with partial data")

        return data

    def _fetch_video_statistics(
        self, video_id: str, credentials: Credentials
    ) -> dict:
        """Fetch basic video stats from YouTube Data API v3."""
        try:
            youtube = build("youtube", "v3", credentials=credentials)
            response = (
                youtube.videos()
                .list(part="statistics", id=video_id)
                .execute()
            )
            items = response.get("items", [])
            if not items:
                return {}

            stats = items[0].get("statistics", {})
            return {
                "viewCount": _safe_int(stats.get("viewCount")),
                "likeCount": _safe_int(stats.get("likeCount")),
                "dislikeCount": _safe_int(stats.get("dislikeCount")),
                "commentCount": _safe_int(stats.get("commentCount")),
            }
        except Exception as e:
            raise YouTubeAPIError(
                message=f"Failed to fetch video statistics: {e}",
                details={"video_id": video_id},
            )

    def _fetch_analytics_overview(
        self, video_id: str, channel_id: str, credentials: Credentials
    ) -> dict:
        """Fetch overview metrics from YouTube Analytics API."""
        try:
            analytics = build("youtubeAnalytics", "v2", credentials=credentials)
            response = analytics.reports().query(
                ids=f"channel=={channel_id}",
                startDate="2000-01-01",
                endDate="2099-12-31",
                metrics="averageViewDuration,averageViewPercentage,shares",
                filters=f"video=={video_id}",
            ).execute()

            rows = response.get("rows", [])
            if not rows:
                return {}

            row = rows[0]
            return {
                "averageViewDuration": row[0] if len(row) > 0 else None,
                "averageViewPercentage": row[1] if len(row) > 1 else None,
                "shares": _safe_int(row[2]) if len(row) > 2 else None,
            }
        except Exception as e:
            raise YouTubeAPIError(
                message=f"Failed to fetch analytics overview: {e}",
                details={"video_id": video_id},
            )

    def _fetch_retention_curve(
        self, video_id: str, channel_id: str, credentials: Credentials
    ) -> list[RetentionPoint]:
        """Fetch the audience retention curve (100 data points).

        Uses the elapsedVideoTimeRatio dimension which returns exactly 100
        equally-spaced data points with audienceWatchRatio and
        relativeRetentionPerformance metrics.
        """
        try:
            analytics = build("youtubeAnalytics", "v2", credentials=credentials)
            response = analytics.reports().query(
                ids=f"channel=={channel_id}",
                startDate="2000-01-01",
                endDate="2099-12-31",
                dimensions="elapsedVideoTimeRatio",
                metrics="audienceWatchRatio,relativeRetentionPerformance",
                filters=f"video=={video_id}",
                sort="elapsedVideoTimeRatio",
            ).execute()

            rows = response.get("rows", [])
            points = []
            for row in rows:
                points.append(RetentionPoint(
                    elapsed_ratio=float(row[0]),
                    audience_watch_ratio=float(row[1]),
                    relative_retention=float(row[2]) if len(row) > 2 else 1.0,
                ))

            logger.info("Fetched %d retention curve points", len(points))
            return points

        except Exception as e:
            raise YouTubeAPIError(
                message=f"Failed to fetch retention curve: {e}",
                details={"video_id": video_id},
            )

    def _fetch_traffic_sources(
        self, video_id: str, channel_id: str, credentials: Credentials
    ) -> dict:
        """Fetch traffic source breakdown."""
        try:
            analytics = build("youtubeAnalytics", "v2", credentials=credentials)
            response = analytics.reports().query(
                ids=f"channel=={channel_id}",
                startDate="2000-01-01",
                endDate="2099-12-31",
                dimensions="insightTrafficSourceType",
                metrics="views",
                filters=f"video=={video_id}",
                sort="-views",
            ).execute()

            rows = response.get("rows", [])
            total = sum(row[1] for row in rows) if rows else 1
            sources = {}
            for row in rows:
                source_type = row[0]
                views = row[1]
                sources[source_type] = round(views / max(total, 1) * 100, 2)

            return sources

        except Exception as e:
            raise YouTubeAPIError(
                message=f"Failed to fetch traffic sources: {e}",
                details={"video_id": video_id},
            )

    def _fetch_demographics(
        self, video_id: str, channel_id: str, credentials: Credentials
    ) -> dict:
        """Fetch age group and gender demographics."""
        try:
            analytics = build("youtubeAnalytics", "v2", credentials=credentials)
            response = analytics.reports().query(
                ids=f"channel=={channel_id}",
                startDate="2000-01-01",
                endDate="2099-12-31",
                dimensions="ageGroup,gender",
                metrics="viewerPercentage",
                filters=f"video=={video_id}",
            ).execute()

            rows = response.get("rows", [])
            demo = {}
            for row in rows:
                age_group = row[0]
                gender = row[1]
                percentage = row[2]
                if age_group not in demo:
                    demo[age_group] = {}
                demo[age_group][gender] = round(percentage, 2)

            return demo

        except Exception as e:
            raise YouTubeAPIError(
                message=f"Failed to fetch demographics: {e}",
                details={"video_id": video_id},
            )

    def _fetch_geographies(
        self, video_id: str, channel_id: str, credentials: Credentials
    ) -> list[dict]:
        """Fetch top countries by views."""
        try:
            analytics = build("youtubeAnalytics", "v2", credentials=credentials)
            response = analytics.reports().query(
                ids=f"channel=={channel_id}",
                startDate="2000-01-01",
                endDate="2099-12-31",
                dimensions="country",
                metrics="views,estimatedMinutesWatched",
                filters=f"video=={video_id}",
                sort="-views",
                maxResults=10,
            ).execute()

            rows = response.get("rows", [])
            total_views = sum(row[1] for row in rows) if rows else 1
            geos = []
            for row in rows:
                geos.append({
                    "country_code": row[0],
                    "views": row[1],
                    "percentage": round(row[1] / max(total_views, 1) * 100, 2),
                    "estimated_minutes_watched": row[2] if len(row) > 2 else None,
                })

            return geos

        except Exception as e:
            raise YouTubeAPIError(
                message=f"Failed to fetch geographies: {e}",
                details={"video_id": video_id},
            )


    def _fetch_top_comments(
        self, video_id: str, credentials: Credentials, max_results: int = 50
    ) -> list[dict]:
        """Fetch top comments (by relevance) from YouTube Data API.

        Uses OAuth credentials first. If that fails with permissions error,
        falls back to fetching without auth (works for public videos).
        """
        try:
            try:
                youtube = build("youtube", "v3", credentials=credentials)
                response = (
                    youtube.commentThreads()
                    .list(part="snippet", videoId=video_id, order="relevance",
                          maxResults=max_results, textFormat="plainText")
                    .execute()
                )
            except Exception:
                # Fall back to unauthenticated request for public comments
                logger.info("OAuth comment fetch failed, trying unauthenticated")
                from app.config import settings
                youtube = build("youtube", "v3", developerKey=settings.google_api_key) if settings.google_api_key else build("youtube", "v3", credentials=credentials)
                response = (
                    youtube.commentThreads()
                    .list(part="snippet", videoId=video_id, order="relevance",
                          maxResults=max_results, textFormat="plainText")
                    .execute()
                )
            response = (
                youtube.commentThreads()
                .list(
                    part="snippet",
                    videoId=video_id,
                    order="relevance",
                    maxResults=max_results,
                    textFormat="plainText",
                )
                .execute()
            )

            comments = []
            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "text": snippet.get("textDisplay", ""),
                    "author": snippet.get("authorDisplayName", ""),
                    "likes": snippet.get("likeCount", 0),
                    "published_at": snippet.get("publishedAt", ""),
                })

            logger.info("Fetched %d comments for video %s", len(comments), video_id)
            return comments

        except Exception as e:
            raise YouTubeAPIError(
                message=f"Failed to fetch comments: {e}",
                details={"video_id": video_id},
            )


def _safe_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
