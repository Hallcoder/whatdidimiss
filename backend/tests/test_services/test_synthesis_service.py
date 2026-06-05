from __future__ import annotations

import json

import pytest

from app.services.synthesis_service import SynthesisService, _format_duration


class TestFormatDuration:
    def test_zero(self):
        assert _format_duration(0) == "0:00"

    def test_seconds_only(self):
        assert _format_duration(45) == "0:45"

    def test_minutes_and_seconds(self):
        assert _format_duration(125) == "2:05"

    def test_hours(self):
        assert _format_duration(3661) == "1:01:01"

    def test_none(self):
        assert _format_duration(None) == "0:00"


class TestParseResponse:
    def setup_method(self):
        self.service = SynthesisService.__new__(SynthesisService)

    def test_valid_json(self):
        raw = json.dumps({
            "wins": [{"title": "Great hook", "description": "test", "category": "hook", "confidence": 0.9}],
            "improvements": [],
            "next_post_ideas": [],
            "creative_tweaks": [],
        })
        result = self.service._parse_response(raw)
        assert len(result["wins"]) == 1
        assert result["wins"][0]["title"] == "Great hook"

    def test_missing_keys_get_defaults(self):
        raw = json.dumps({"wins": [{"title": "test", "description": "d"}]})
        result = self.service._parse_response(raw)
        assert result["improvements"] == []
        assert result["next_post_ideas"] == []
        assert result["creative_tweaks"] == []

    def test_invalid_json_raises(self):
        from app.utils.exceptions import OpenAIError

        with pytest.raises(OpenAIError):
            self.service._parse_response("not json {{{")


class TestBuildContext:
    def setup_method(self):
        self.service = SynthesisService.__new__(SynthesisService)

    def test_context_has_required_keys(self):
        ctx = self.service._build_context(
            video_meta={"title": "Test", "duration_seconds": 300},
            segments=[{
                "segment_index": 0, "start_ms": 0, "end_ms": 30000,
                "segment_type": "intro_hook", "pacing_score": 5.0,
                "labels": ["cat"], "transcript_text": "Hello",
                "engagement_label": "high_retention",
                "avg_retention": 0.85, "retention_delta": -0.02,
            }],
            engagement={
                "views": 1000, "likes": 50, "comments": 10,
                "avg_view_duration_seconds": 180,
                "avg_view_percentage": 60.0,
                "traffic_sources": {"SEARCH": 40, "SUGGESTED": 30},
            },
            retention_curve=[
                {"elapsed_ratio": 0.0, "watch_ratio": 0.9, "relative_retention": 1.0},
                {"elapsed_ratio": 1.0, "watch_ratio": 0.3, "relative_retention": 0.8},
            ],
            labels=["cat", "animal", "pet"],
        )
        assert ctx["title"] == "Test"
        assert ctx["duration_formatted"] == "5:00"
        assert ctx["views"] == 1000
        assert "cat" in ctx["labels"]
        assert "SEARCH" in ctx["traffic_sources"]
