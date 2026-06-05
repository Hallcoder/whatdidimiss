from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.channel import Channel
from app.models.user import User
from app.services.youtube_data_service import YouTubeDataService
from app.utils.exceptions import AuthenticationError

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 15
REFRESH_TOKEN_EXPIRY_DAYS = 7

# In-memory store for PKCE code verifiers keyed by state
_code_verifiers: dict = {}


class AuthService:
    def __init__(self):
        self._fernet = Fernet(settings.fernet_key.encode()) if settings.fernet_key != "change-me-generate-with-cryptography-fernet" else None

    def _encrypt(self, value: str) -> str:
        if self._fernet:
            return self._fernet.encrypt(value.encode()).decode()
        return value

    def _decrypt(self, value: str) -> str:
        if self._fernet:
            return self._fernet.decrypt(value.encode()).decode()
        return value

    def _create_flow(self) -> Flow:
        client_config = {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_redirect_uri],
            }
        }
        flow = Flow.from_client_config(client_config, scopes=SCOPES)
        flow.redirect_uri = settings.google_redirect_uri
        return flow

    def generate_auth_url(self) -> tuple[str, str]:
        flow = self._create_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        # Store the code verifier for PKCE
        _code_verifiers[state] = flow.code_verifier
        return auth_url, state

    async def handle_callback(
        self, code: str, state: str, db: AsyncSession
    ) -> tuple[User, str, str]:
        flow = self._create_flow()
        # Restore the PKCE code verifier from the auth step
        flow.code_verifier = _code_verifiers.pop(state, None)
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Verify and decode the ID token
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            settings.google_client_id,
        )

        google_id = id_info["sub"]
        email = id_info.get("email", "")
        display_name = id_info.get("name")
        avatar_url = id_info.get("picture")

        # Upsert user
        result = await db.execute(select(User).where(User.google_id == google_id))
        user = result.scalar_one_or_none()

        encrypted_access = self._encrypt(credentials.token)
        encrypted_refresh = self._encrypt(credentials.refresh_token) if credentials.refresh_token else ""

        if user:
            user.email = email
            user.display_name = display_name
            user.avatar_url = avatar_url
            user.access_token = encrypted_access
            if credentials.refresh_token:
                user.refresh_token = encrypted_refresh
            user.token_expiry = credentials.expiry
            user.scopes_granted = list(credentials.scopes) if credentials.scopes else SCOPES
        else:
            user = User(
                google_id=google_id,
                email=email,
                display_name=display_name,
                avatar_url=avatar_url,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                token_expiry=credentials.expiry,
                scopes_granted=list(credentials.scopes) if credentials.scopes else SCOPES,
            )
            db.add(user)

        await db.flush()

        # Fetch and link YouTube channels
        await self._sync_user_channels(user, credentials, db)

        # Generate app-level tokens
        access_token = self._create_jwt(str(user.id))
        refresh_token = self._create_refresh_token(str(user.id))

        return user, access_token, refresh_token

    async def _sync_user_channels(self, user: User, credentials, db: AsyncSession) -> None:
        """Fetch user's YouTube channels and upsert them in the database."""
        try:
            yt_service = YouTubeDataService()
            channels = yt_service.fetch_user_channels(credentials)

            for ch_info in channels:
                result = await db.execute(
                    select(Channel).where(Channel.youtube_channel_id == ch_info.channel_id)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    existing.channel_title = ch_info.title
                    existing.subscriber_count = ch_info.subscriber_count
                    existing.user_id = user.id
                else:
                    channel = Channel(
                        user_id=user.id,
                        youtube_channel_id=ch_info.channel_id,
                        channel_title=ch_info.title,
                        subscriber_count=ch_info.subscriber_count,
                    )
                    db.add(channel)

            await db.flush()
        except Exception:
            # Don't fail the entire OAuth flow if channel sync fails
            import logging
            logging.getLogger(__name__).exception("Failed to sync YouTube channels")

    async def refresh_app_token(
        self, refresh_token: str | None, db: AsyncSession
    ) -> tuple[User, str, str]:
        if not refresh_token:
            raise AuthenticationError(message="No refresh token provided")

        try:
            payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[JWT_ALGORITHM])
            if payload.get("type") != "refresh":
                raise AuthenticationError(message="Invalid token type")
            user_id = payload.get("sub")
        except Exception:
            raise AuthenticationError(message="Invalid or expired refresh token")

        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            raise AuthenticationError(message="User not found")

        access_token = self._create_jwt(str(user.id))
        new_refresh = self._create_refresh_token(str(user.id))

        return user, access_token, new_refresh

    def _create_jwt(self, user_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(minutes=JWT_EXPIRY_MINUTES),
            "type": "access",
        }
        return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)

    def _create_refresh_token(self, user_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
            "type": "refresh",
        }
        return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)

    async def get_google_credentials(self, user_id: uuid.UUID, db: AsyncSession):
        """Retrieve and decrypt stored Google credentials for YouTube API calls."""
        from google.oauth2.credentials import Credentials

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise AuthenticationError(message="User not found")

        access_token = self._decrypt(user.access_token)
        refresh_token = self._decrypt(user.refresh_token)

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(google_requests.Request())
            user.access_token = self._encrypt(creds.token)
            user.token_expiry = creds.expiry
            await db.flush()

        return creds
