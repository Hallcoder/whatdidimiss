from __future__ import annotations

import logging
import re
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.utils.exceptions import YouTubeAPIError

logger = logging.getLogger(__name__)


class YouTubeCaptionsService:
    """Fetches captions/subtitles from YouTube videos."""

    def fetch_transcript(self, video_id: str, credentials: Credentials) -> Optional[list[dict]]:
        """Fetch captions for a video. Tries auto-generated first, then manual."""
        try:
            youtube = build("youtube", "v3", credentials=credentials)

            # List available captions
            captions_response = youtube.captions().list(
                part="snippet", videoId=video_id
            ).execute()

            items = captions_response.get("items", [])
            if not items:
                logger.info("No captions available for video %s", video_id)
                return None

            # Prefer English, then any language
            caption_id = None
            for item in items:
                lang = item["snippet"].get("language", "")
                track_kind = item["snippet"].get("trackKind", "")
                if lang.startswith("en"):
                    caption_id = item["id"]
                    break
            if not caption_id and items:
                caption_id = items[0]["id"]

            if not caption_id:
                return None

            # Download the caption track
            caption_data = youtube.captions().download(
                id=caption_id, tfmt="srt"
            ).execute()

            if isinstance(caption_data, bytes):
                caption_data = caption_data.decode("utf-8")

            return _parse_srt(caption_data)

        except Exception as e:
            logger.warning("Failed to fetch captions via API: %s. Trying yt-dlp fallback.", e)
            return self._fetch_via_ytdlp(video_id)

    def _fetch_via_ytdlp(self, video_id: str) -> Optional[list[dict]]:
        """Fallback: fetch subtitles using yt-dlp."""
        try:
            import json
            import yt_dlp

            url = f"https://www.youtube.com/watch?v={video_id}"
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en", "en-US", "en-GB"],
                "subtitlesformat": "json3",
            }

            from app.config import settings
            if settings.ytdlp_cookies_file:
                ydl_opts["cookiefile"] = settings.ytdlp_cookies_file

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # Check for subtitles in the info
                subs = info.get("requested_subtitles") or {}
                auto_subs = info.get("automatic_captions") or {}
                manual_subs = info.get("subtitles") or {}

                # Try to get English subtitles
                sub_data = None
                for lang_key in ["en", "en-US", "en-GB"]:
                    if lang_key in subs:
                        sub_url = subs[lang_key].get("url")
                        if sub_url:
                            import urllib.request
                            with urllib.request.urlopen(sub_url) as resp:
                                sub_data = json.loads(resp.read().decode())
                            break
                    if lang_key in auto_subs:
                        for fmt in auto_subs[lang_key]:
                            if fmt.get("ext") == "json3":
                                import urllib.request
                                with urllib.request.urlopen(fmt["url"]) as resp:
                                    sub_data = json.loads(resp.read().decode())
                                break
                        if sub_data:
                            break

                if not sub_data:
                    logger.info("No English subtitles found for %s", video_id)
                    return None

                # Parse json3 format
                events = sub_data.get("events", [])
                segments = []
                for event in events:
                    if "segs" not in event:
                        continue
                    start_ms = event.get("tStartMs", 0)
                    duration_ms = event.get("dDurationMs", 0)
                    text = "".join(seg.get("utf8", "") for seg in event["segs"]).strip()
                    if text and text != "\n":
                        segments.append({
                            "text": text,
                            "start_ms": start_ms,
                            "end_ms": start_ms + duration_ms,
                            "confidence": 1.0,
                        })

                logger.info("Fetched %d transcript segments via yt-dlp for %s", len(segments), video_id)
                return segments if segments else None

        except Exception as e:
            logger.warning("yt-dlp caption fallback failed: %s", e)
            return None


def _parse_srt(srt_text: str) -> list[dict]:
    """Parse SRT subtitle format into structured segments."""
    segments = []
    blocks = re.split(r"\n\n+", srt_text.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        # Parse timestamp line: "00:00:01,000 --> 00:00:04,000"
        time_match = re.match(
            r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})",
            lines[1],
        )
        if not time_match:
            continue

        g = time_match.groups()
        start_ms = int(g[0]) * 3600000 + int(g[1]) * 60000 + int(g[2]) * 1000 + int(g[3])
        end_ms = int(g[4]) * 3600000 + int(g[5]) * 60000 + int(g[6]) * 1000 + int(g[7])

        text = " ".join(lines[2:]).strip()
        if text:
            segments.append({
                "text": text,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "confidence": 1.0,
            })

    return segments
