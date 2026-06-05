from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PaginatedResponse(BaseModel):
    items: list[Any]
    page: int
    per_page: int
    total: int
    total_pages: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
