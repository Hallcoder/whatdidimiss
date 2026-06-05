from __future__ import annotations

from pydantic import BaseModel


class AuthURLResponse(BaseModel):
    auth_url: str
    state: str


class ChannelSummary(BaseModel):
    id: str
    youtube_channel_id: str
    channel_title: str | None = None
    subscriber_count: int | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    channel: ChannelSummary | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
