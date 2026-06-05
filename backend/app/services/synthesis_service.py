from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

import openai

from app.config import settings
from app.prompts.synthesis_system import PROMPT_VERSION, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.utils.exceptions import OpenAIError

logger = logging.getLogger(__name__)


class SynthesisService:
    """Orchestrates GPT-4o calls to generate coaching insights from video data."""

    def __init__(self):
        self._client = openai.OpenAI(api_key=settings.openai_api_key)

    def generate_insights(
        self,
        video_meta: dict,
        segments: list[dict],
        engagement: dict,
        retention_curve: list[dict],
        labels: list[str],
        comments: list[dict] | None = None,
        creator_assessment: dict | None = None,
    ) -> dict:
        """Generate insights by sending assembled context to GPT-4o."""
        context = self._build_context(video_meta, segments, engagement, retention_curve, labels, comments, creator_assessment)
        prompt = self._build_user_prompt(context)
        raw_response = self._call_openai(prompt)
        parsed = self._parse_response(raw_response)
        return parsed

    def _build_context(
        self,
        video_meta: dict,
        segments: list[dict],
        engagement: dict,
        retention_curve: list[dict],
        labels: list[str],
        comments: list[dict] | None = None,
        creator_assessment: dict | None = None,
    ) -> dict:
        """Assemble all data into a context dict for prompt formatting."""
        duration_s = video_meta.get("duration_seconds", 0)
        duration_formatted = _format_duration(duration_s)

        # Format segments with engagement data
        segments_data = self._format_segments(segments, duration_s)

        # Traffic sources
        traffic = engagement.get("traffic_sources", {})
        traffic_str = "\n".join(
            f"- {source}: {pct}%" for source, pct in sorted(traffic.items(), key=lambda x: -x[1])
        ) if traffic else "No traffic source data available"

        # Retention analysis
        retention_trend, biggest_dropoff, best_segment = self._analyze_retention(
            segments, retention_curve
        )

        return {
            "title": video_meta.get("title", "Untitled"),
            "duration_formatted": duration_formatted,
            "views": engagement.get("views", "N/A"),
            "likes": engagement.get("likes", "N/A"),
            "comments": engagement.get("comments", "N/A"),
            "avg_view_duration": _format_duration(engagement.get("avg_view_duration_seconds", 0)),
            "avg_view_percentage": round(engagement.get("avg_view_percentage", 0), 1),
            "traffic_sources": traffic_str,
            "segments_data": segments_data,
            "retention_trend": retention_trend,
            "biggest_dropoff": biggest_dropoff,
            "best_segment": best_segment,
            "labels": ", ".join(labels[:15]) if labels else "No labels detected",
            "comments_data": self._format_comments(comments),
            "creator_assessment": self._format_creator_assessment(creator_assessment),
        }

    def _format_comments(self, comments: list[dict] | None) -> str:
        """Format top comments for the prompt."""
        if not comments:
            return "No comment data available"
        lines = []
        for c in comments[:30]:
            likes = c.get("likes", 0)
            text = c.get("text", "").replace("\n", " ")[:200]
            lines.append(f"- [{likes} likes] {text}")
        return "\n".join(lines)

    def _format_creator_assessment(self, assessment: dict | None) -> str:
        """Format creator self-assessment for the prompt."""
        if not assessment:
            return "No self-assessment provided by the creator."

        lines = ["The creator rated themselves before seeing any AI analysis:"]

        score_labels = {
            "hook_score": "Hook effectiveness",
            "structure_score": "Script structure",
            "clarity_score": "Clarity of explanation",
            "cta_score": "Call to action",
            "energy_score": "Energy/delivery",
            "pacing_score": "Pacing",
            "visual_score": "Visual quality",
        }

        for key, label in score_labels.items():
            val = assessment.get(key)
            if val is not None:
                lines.append(f"- {label}: {val}/10")

        best = assessment.get("best_part")
        if best:
            lines.append(f'\nWhat they think worked best: "{best}"')

        change = assessment.get("would_change")
        if change:
            lines.append(f'\nWhat they would change: "{change}"')

        return "\n".join(lines)

    def _format_segments(self, segments: list[dict], duration_s: int) -> str:
        """Format segment data into a readable string for the prompt."""
        lines = []
        for seg in segments:
            start = _format_duration(seg.get("start_ms", 0) / 1000)
            end = _format_duration(seg.get("end_ms", 0) / 1000)
            seg_type = seg.get("segment_type", "unknown")
            pacing = seg.get("pacing_score", 0)

            # Engagement data
            eng_label = seg.get("engagement_label", "no data")
            avg_ret = seg.get("avg_retention")
            ret_delta = seg.get("retention_delta")
            transcript = seg.get("transcript_text", "")

            ret_str = f"{avg_ret:.1%}" if avg_ret is not None else "N/A"
            delta_str = f"{ret_delta:+.1%}" if ret_delta is not None else "N/A"

            line = (
                f"Segment {seg['segment_index']} [{start} - {end}] "
                f"type={seg_type} | pacing={pacing:.1f} shots/min | "
                f"retention={ret_str} (delta={delta_str}) | label={eng_label}"
            )

            seg_labels = seg.get("labels", [])
            if seg_labels:
                line += f"\n  Labels: {', '.join(seg_labels[:5])}"

            if transcript:
                # Truncate transcript to keep prompt size reasonable
                snippet = transcript[:300] + "..." if len(transcript) > 300 else transcript
                line += f"\n  Transcript: \"{snippet}\""

            lines.append(line)

        return "\n\n".join(lines) if lines else "No segment data available"

    def _analyze_retention(
        self, segments: list[dict], retention_curve: list[dict]
    ) -> tuple:
        """Summarize retention patterns for the prompt."""
        if not retention_curve:
            return ("No retention data", "N/A", "N/A")

        # Overall trend
        first_quarter = [p["watch_ratio"] for p in retention_curve[:25]]
        last_quarter = [p["watch_ratio"] for p in retention_curve[75:]]
        avg_first = sum(first_quarter) / len(first_quarter) if first_quarter else 0
        avg_last = sum(last_quarter) / len(last_quarter) if last_quarter else 0
        overall_drop = avg_first - avg_last

        if overall_drop < 0.15:
            trend = f"Strong retention — only {overall_drop:.0%} drop from start to end"
        elif overall_drop < 0.35:
            trend = f"Moderate retention — {overall_drop:.0%} drop from start to end"
        else:
            trend = f"Significant drop-off — {overall_drop:.0%} lost from start to end"

        # Biggest drop-off segment
        dropoff_seg = None
        worst_delta = 0
        for seg in segments:
            delta = seg.get("retention_delta")
            if delta is not None and delta < worst_delta:
                worst_delta = delta
                dropoff_seg = seg

        if dropoff_seg:
            start = _format_duration(dropoff_seg["start_ms"] / 1000)
            end = _format_duration(dropoff_seg["end_ms"] / 1000)
            biggest_dropoff = (
                f"Segment {dropoff_seg['segment_index']} ({start}-{end}): "
                f"{worst_delta:+.1%} retention change"
            )
        else:
            biggest_dropoff = "No significant drop-offs detected"

        # Best segment
        best_seg = None
        best_ret = 0
        for seg in segments:
            ret = seg.get("avg_retention")
            if ret is not None and ret > best_ret:
                best_ret = ret
                best_seg = seg

        if best_seg:
            start = _format_duration(best_seg["start_ms"] / 1000)
            end = _format_duration(best_seg["end_ms"] / 1000)
            best_segment = (
                f"Segment {best_seg['segment_index']} ({start}-{end}): "
                f"{best_ret:.1%} avg retention, type={best_seg.get('segment_type', 'unknown')}"
            )
        else:
            best_segment = "Insufficient data"

        return (trend, biggest_dropoff, best_segment)

    def _build_user_prompt(self, context: dict) -> str:
        """Format the user prompt template with context data."""
        return USER_PROMPT_TEMPLATE.format(**context)

    def _call_openai(self, user_prompt: str) -> str:
        """Call GPT-4o and return the raw response content."""
        try:
            response = self._client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=settings.openai_temperature,
                max_tokens=settings.openai_max_tokens,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            logger.info(
                "GPT-4o response: %d tokens used (prompt=%d, completion=%d)",
                response.usage.total_tokens,
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
            )
            return content

        except openai.RateLimitError as e:
            raise OpenAIError(
                message="OpenAI rate limit exceeded",
                details={"error": str(e)},
            )
        except openai.APIError as e:
            raise OpenAIError(
                message=f"OpenAI API error: {e}",
                details={"error": str(e)},
            )
        except Exception as e:
            raise OpenAIError(
                message=f"Failed to call OpenAI: {e}",
                details={"error": str(e)},
            )

    def _parse_response(self, raw_content: str) -> dict:
        """Parse the GPT-4o JSON response into a structured dict."""
        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError as e:
            raise OpenAIError(
                message=f"GPT-4o returned invalid JSON: {e}",
                details={"raw_content": raw_content[:500]},
            )

        # Validate expected keys exist
        expected_keys = ["wins", "improvements", "next_post_ideas", "creative_tweaks"]
        for key in expected_keys:
            if key not in parsed:
                parsed[key] = []

        return parsed

    def get_model_version(self) -> str:
        return settings.openai_model

    def get_prompt_version(self) -> str:
        return PROMPT_VERSION


def _format_duration(seconds) -> str:
    """Format seconds into human-readable duration (e.g., '5:32' or '1:02:15')."""
    if seconds is None or seconds == 0:
        return "0:00"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
