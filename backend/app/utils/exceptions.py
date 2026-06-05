from __future__ import annotations

from typing import Any


class AppException(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        if code:
            self.code = code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppException):
    status_code = 401
    code = "AUTHENTICATION_ERROR"


class AuthorizationError(AppException):
    status_code = 403
    code = "AUTHORIZATION_ERROR"


class NotFoundError(AppException):
    status_code = 404
    code = "NOT_FOUND"


class ValidationError(AppException):
    status_code = 422
    code = "VALIDATION_ERROR"


class ConflictError(AppException):
    status_code = 409
    code = "CONFLICT"


class RateLimitError(AppException):
    status_code = 429
    code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None, **kwargs):
        super().__init__(message=message, **kwargs)
        self.retry_after = retry_after


class ExternalServiceError(AppException):
    status_code = 502
    code = "EXTERNAL_SERVICE_ERROR"


class YouTubeAPIError(ExternalServiceError):
    code = "YOUTUBE_API_ERROR"


class VideoIntelligenceError(ExternalServiceError):
    code = "VIDEO_INTELLIGENCE_ERROR"


class OpenAIError(ExternalServiceError):
    code = "OPENAI_ERROR"


class GCSError(ExternalServiceError):
    code = "GCS_ERROR"
