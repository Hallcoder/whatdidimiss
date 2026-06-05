from __future__ import annotations

from app.services.video_ingest_service import extract_video_id
from app.services.youtube_data_service import _parse_iso8601_duration


class TestExtractVideoId:
    def test_standard_url(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_url_with_extra_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120&list=PLfoo"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_invalid_url(self):
        assert extract_video_id("https://example.com/video") is None

    def test_empty_string(self):
        assert extract_video_id("") is None


class TestParseIsoDuration:
    def test_hours_minutes_seconds(self):
        assert _parse_iso8601_duration("PT1H2M10S") == 3730

    def test_minutes_seconds(self):
        assert _parse_iso8601_duration("PT5M30S") == 330

    def test_seconds_only(self):
        assert _parse_iso8601_duration("PT45S") == 45

    def test_minutes_only(self):
        assert _parse_iso8601_duration("PT10M") == 600

    def test_hours_only(self):
        assert _parse_iso8601_duration("PT2H") == 7200

    def test_invalid_format(self):
        assert _parse_iso8601_duration("invalid") == 0

    def test_empty(self):
        assert _parse_iso8601_duration("") == 0
