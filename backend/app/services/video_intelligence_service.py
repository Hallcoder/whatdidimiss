from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from google.cloud import videointelligence_v1 as vi

from app.config import settings
from app.utils.exceptions import VideoIntelligenceError

logger = logging.getLogger(__name__)


@dataclass
class LabelAnnotation:
    description: str
    category: Optional[str]
    confidence: float
    segments: list[dict] = field(default_factory=list)


@dataclass
class ShotChange:
    start_ms: int
    end_ms: int


@dataclass
class TextDetection:
    text: str
    confidence: float
    start_ms: int
    end_ms: int


@dataclass
class TranscriptSegment:
    text: str
    confidence: float
    start_ms: int
    end_ms: int
    words: list[dict] = field(default_factory=list)


@dataclass
class VideoIntelligenceResult:
    labels: list[LabelAnnotation]
    shot_changes: list[ShotChange]
    text_detections: list[TextDetection]
    transcript: list[TranscriptSegment]
    raw_response: dict


def _offset_to_ms(offset) -> int:
    """Convert a protobuf Duration or timedelta offset to milliseconds."""
    import datetime
    if isinstance(offset, datetime.timedelta):
        return int(offset.total_seconds() * 1000)
    # Protobuf Duration object
    return int(offset.seconds * 1000 + getattr(offset, 'nanos', 0) / 1_000_000)


class VideoIntelligenceService:
    """Wraps Google Video Intelligence API for video analysis."""

    def __init__(self):
        self._client: Optional[vi.VideoIntelligenceServiceClient] = None

    @property
    def client(self) -> vi.VideoIntelligenceServiceClient:
        if self._client is None:
            self._client = vi.VideoIntelligenceServiceClient()
        return self._client

    def analyze_video(self, gcs_uri: str) -> VideoIntelligenceResult:
        """Run full analysis on a video stored in GCS.

        Requests label detection, shot change detection, text detection,
        and speech transcription. Blocks until the long-running operation completes.
        """
        features = [
            vi.Feature.LABEL_DETECTION,
            vi.Feature.SHOT_CHANGE_DETECTION,
            vi.Feature.TEXT_DETECTION,
            vi.Feature.SPEECH_TRANSCRIPTION,
        ]

        speech_config = vi.SpeechTranscriptionConfig(
            language_code="en-US",
            enable_automatic_punctuation=True,
        )
        video_context = vi.VideoContext(
            speech_transcription_config=speech_config,
        )

        try:
            logger.info("Starting Video Intelligence analysis for %s", gcs_uri)
            operation = self.client.annotate_video(
                request=vi.AnnotateVideoRequest(
                    input_uri=gcs_uri,
                    features=features,
                    video_context=video_context,
                )
            )

            logger.info("Waiting for Video Intelligence operation to complete...")
            response = operation.result(timeout=600)
            logger.info("Video Intelligence analysis complete")

        except Exception as e:
            raise VideoIntelligenceError(
                message=f"Video Intelligence API failed: {e}",
                details={"gcs_uri": gcs_uri},
            )

        if not response.annotation_results:
            raise VideoIntelligenceError(
                message="Video Intelligence returned no annotation results",
                details={"gcs_uri": gcs_uri},
            )

        result = response.annotation_results[0]

        labels = self._parse_labels(result)
        shot_changes = self._parse_shot_changes(result)
        text_detections = self._parse_text_detections(result)
        transcript = self._parse_transcript(result)

        raw = self._build_raw_response(labels, shot_changes, text_detections, transcript)

        return VideoIntelligenceResult(
            labels=labels,
            shot_changes=shot_changes,
            text_detections=text_detections,
            transcript=transcript,
            raw_response=raw,
        )

    def _parse_labels(self, result) -> list[LabelAnnotation]:
        """Parse segment-level and shot-level label annotations."""
        labels = []

        for annotation in result.segment_label_annotations:
            category = None
            if annotation.category_entities:
                category = annotation.category_entities[0].description

            segments = []
            max_confidence = 0.0
            for segment in annotation.segments:
                conf = segment.confidence
                max_confidence = max(max_confidence, conf)
                segments.append({
                    "start_ms": _offset_to_ms(segment.segment.start_time_offset),
                    "end_ms": _offset_to_ms(segment.segment.end_time_offset),
                    "confidence": round(conf, 4),
                })

            labels.append(LabelAnnotation(
                description=annotation.entity.description,
                category=category,
                confidence=round(max_confidence, 4),
                segments=segments,
            ))

        # Sort by confidence descending
        labels.sort(key=lambda l: l.confidence, reverse=True)
        return labels

    def _parse_shot_changes(self, result) -> list[ShotChange]:
        """Parse shot change annotations into start/end ms pairs."""
        shots = []
        for annotation in result.shot_annotations:
            shots.append(ShotChange(
                start_ms=_offset_to_ms(annotation.start_time_offset),
                end_ms=_offset_to_ms(annotation.end_time_offset),
            ))

        # Sort by start time
        shots.sort(key=lambda s: s.start_ms)
        return shots

    def _parse_text_detections(self, result) -> list[TextDetection]:
        """Parse text/OCR detection annotations."""
        detections = []
        for annotation in result.text_annotations:
            text = annotation.text
            for text_segment in annotation.segments:
                conf = text_segment.confidence
                start = _offset_to_ms(text_segment.segment.start_time_offset)
                end = _offset_to_ms(text_segment.segment.end_time_offset)
                detections.append(TextDetection(
                    text=text,
                    confidence=round(conf, 4),
                    start_ms=start,
                    end_ms=end,
                ))

        detections.sort(key=lambda d: d.start_ms)
        return detections

    def _parse_transcript(self, result) -> list[TranscriptSegment]:
        """Parse speech transcription results."""
        segments = []
        for transcription in result.speech_transcriptions:
            for alternative in transcription.alternatives:
                if not alternative.transcript:
                    continue

                words = []
                start_ms = 0
                end_ms = 0
                for i, word_info in enumerate(alternative.words):
                    w_start = _offset_to_ms(word_info.start_time)
                    w_end = _offset_to_ms(word_info.end_time)
                    if i == 0:
                        start_ms = w_start
                    end_ms = w_end
                    words.append({
                        "word": word_info.word,
                        "start_ms": w_start,
                        "end_ms": w_end,
                        "confidence": round(word_info.confidence, 4) if word_info.confidence else None,
                    })

                segments.append(TranscriptSegment(
                    text=alternative.transcript.strip(),
                    confidence=round(alternative.confidence, 4) if alternative.confidence else 0.0,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    words=words,
                ))

                # Only take the top alternative per transcription
                break

        segments.sort(key=lambda s: s.start_ms)
        return segments

    def _build_raw_response(
        self,
        labels: list[LabelAnnotation],
        shot_changes: list[ShotChange],
        text_detections: list[TextDetection],
        transcript: list[TranscriptSegment],
    ) -> dict:
        """Build a JSON-serializable dict from parsed results for storage."""
        return {
            "labels": [
                {
                    "description": l.description,
                    "category": l.category,
                    "confidence": l.confidence,
                    "segments": l.segments,
                }
                for l in labels
            ],
            "shot_changes": [
                {"start_ms": s.start_ms, "end_ms": s.end_ms}
                for s in shot_changes
            ],
            "text_detections": [
                {
                    "text": t.text,
                    "confidence": t.confidence,
                    "start_ms": t.start_ms,
                    "end_ms": t.end_ms,
                }
                for t in text_detections
            ],
            "transcript": [
                {
                    "text": t.text,
                    "confidence": t.confidence,
                    "start_ms": t.start_ms,
                    "end_ms": t.end_ms,
                    "words": t.words,
                }
                for t in transcript
            ],
        }
