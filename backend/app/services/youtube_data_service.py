from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.utils.exceptions import NotFoundError, YouTubeAPIError

logger = logging.getLogger(__name__)


@dataclass
class VideoMetadata:
    youtube_video_id: str
    title: str
    description: str
    channel_id: str
    published_at: str
    duration_seconds: int
    thumbnail_url: Optional[str]


@dataclass
class ChannelInfo:
    channel_id: str
    title: str
    subscriber_count: Optional[int]


@dataclass
class ChannelVideoItem:
    youtube_video_id: str
    title: str
    thumbnail_url: Optional[str]
    duration_seconds: int
    published_at: str
    view_count: Optional[int]


@dataclass
class ChannelVideosPage:
    items: list[ChannelVideoItem]
    next_page_token: Optional[str]
    total_results: Optional[int]


class YouTubeDataService:
    """Wraps YouTube Data API v3 for video metadata and channel info."""

    def _build_client(self, credentials: Credentials):
        return build("youtube", "v3", credentials=credentials)

    def fetch_video_metadata(self, video_id: str, credentials: Credentials) -> VideoMetadata:
        """Fetch video metadata from YouTube Data API."""
        try:
            youtube = self._build_client(credentials)
            response = (
                youtube.videos()
                .list(part="snippet,contentDetails,statistics", id=video_id)
                .execute()
            )

            items = response.get("items", [])
            if not items:
                raise NotFoundError(message=f"YouTube video {video_id} not found")

            item = items[0]
            snippet = item["snippet"]
            content_details = item["contentDetails"]

            duration_seconds = _parse_iso8601_duration(content_details["duration"])

            thumbnails = snippet.get("thumbnails", {})
            thumbnail_url = (
                thumbnails.get("maxres", {}).get("url")
                or thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url")
            )

            return VideoMetadata(
                youtube_video_id=video_id,
                title=snippet.get("title", ""),
                description=snippet.get("description", ""),
                channel_id=snippet.get("channelId", ""),
                published_at=snippet.get("publishedAt", ""),
                duration_seconds=duration_seconds,
                thumbnail_url=thumbnail_url,
            )
        except NotFoundError:
            raise
        except Exception as e:
            raise YouTubeAPIError(
                message=f"Failed to fetch video metadata: {e}",
                details={"video_id": video_id},
            )

    def fetch_channel_videos(
        self,
        channel_id: str,
        credentials: Credentials,
        page_token: Optional[str] = None,
        max_results: int = 20,
    ) -> ChannelVideosPage:
        """Fetch videos from a channel's uploads playlist."""
        try:
            youtube = self._build_client(credentials)

            # Get the uploads playlist ID for this channel
            channel_resp = (
                youtube.channels()
                .list(part="contentDetails", id=channel_id)
                .execute()
            )
            items = channel_resp.get("items", [])
            if not items:
                raise NotFoundError(message=f"Channel {channel_id} not found")

            uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

            # Fetch playlist items
            request_kwargs = {
                "part": "snippet",
                "playlistId": uploads_playlist_id,
                "maxResults": max_results,
            }
            if page_token:
                request_kwargs["pageToken"] = page_token

            playlist_resp = (
                youtube.playlistItems().list(**request_kwargs).execute()
            )

            video_ids = [
                item["snippet"]["resourceId"]["videoId"]
                for item in playlist_resp.get("items", [])
                if item["snippet"]["resourceId"]["kind"] == "youtube#video"
            ]

            if not video_ids:
                return ChannelVideosPage(items=[], next_page_token=None, total_results=0)

            # Fetch video details (duration, view count) in a single batch
            details_resp = (
                youtube.videos()
                .list(
                    part="contentDetails,statistics,snippet",
                    id=",".join(video_ids),
                )
                .execute()
            )

            details_map = {}
            for item in details_resp.get("items", []):
                details_map[item["id"]] = item

            result_items = []
            for vid_id in video_ids:
                detail = details_map.get(vid_id)
                if not detail:
                    continue

                snippet = detail["snippet"]
                stats = detail.get("statistics", {})
                content = detail.get("contentDetails", {})

                thumbnails = snippet.get("thumbnails", {})
                thumbnail_url = (
                    thumbnails.get("medium", {}).get("url")
                    or thumbnails.get("default", {}).get("url")
                )

                view_count_str = stats.get("viewCount")
                view_count = int(view_count_str) if view_count_str else None

                result_items.append(
                    ChannelVideoItem(
                        youtube_video_id=vid_id,
                        title=snippet.get("title", ""),
                        thumbnail_url=thumbnail_url,
                        duration_seconds=_parse_iso8601_duration(content.get("duration", "PT0S")),
                        published_at=snippet.get("publishedAt", ""),
                        view_count=view_count,
                    )
                )

            return ChannelVideosPage(
                items=result_items,
                next_page_token=playlist_resp.get("nextPageToken"),
                total_results=playlist_resp.get("pageInfo", {}).get("totalResults"),
            )
        except NotFoundError:
            raise
        except Exception as e:
            raise YouTubeAPIError(
                message=f"Failed to fetch channel videos: {e}",
                details={"channel_id": channel_id},
            )

    def fetch_user_channels(self, credentials: Credentials) -> list[ChannelInfo]:
        """Fetch the authenticated user's YouTube channels."""
        try:
            youtube = self._build_client(credentials)
            response = (
                youtube.channels()
                .list(part="snippet,statistics", mine=True)
                .execute()
            )

            channels = []
            for item in response.get("items", []):
                snippet = item["snippet"]
                statistics = item.get("statistics", {})
                subscriber_count = statistics.get("subscriberCount")

                channels.append(
                    ChannelInfo(
                        channel_id=item["id"],
                        title=snippet.get("title", ""),
                        subscriber_count=int(subscriber_count) if subscriber_count else None,
                    )
                )

            return channels
        except Exception as e:
            raise YouTubeAPIError(
                message=f"Failed to fetch user channels: {e}",
            )


def _parse_iso8601_duration(duration_str: str) -> int:
    """Parse ISO 8601 duration (e.g., PT1H2M10S) to total seconds."""
    match = re.match(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        duration_str,
    )
    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds
