import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory
from app.utils.exceptions import AuthenticationError


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User

    if settings.auth_disabled:
        from app.models.channel import Channel

        # Return first user or create a dev user + channel
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                google_id="dev-user",
                email="dev@localhost",
                display_name="Dev User",
                access_token="",
                refresh_token="",
            )
            db.add(user)
            await db.flush()

        # Ensure dev user has a channel
        ch_result = await db.execute(select(Channel).where(Channel.user_id == user.id).limit(1))
        if ch_result.scalar_one_or_none() is None:
            channel = Channel(
                user_id=user.id,
                youtube_channel_id="dev-channel",
                channel_title="Dev Channel",
            )
            db.add(channel)
            await db.flush()

        return user

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthenticationError(message="Missing or invalid authorization header")

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError(message="Invalid token payload")
    except JWTError:
        raise AuthenticationError(message="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError(message="User not found")

    return user
