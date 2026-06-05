import json
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.schemas.auth import AuthURLResponse, ChannelSummary, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google/login", response_model=AuthURLResponse)
async def google_login(request: Request):
    auth_service = AuthService()
    auth_url, state = auth_service.generate_auth_url()
    return AuthURLResponse(auth_url=auth_url, state=state)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService()
    user, access_token, refresh_token = await auth_service.handle_callback(
        code=code, state=state, db=db
    )

    user_data = json.dumps({
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
    })

    params = urlencode({"access_token": access_token, "user": user_data})
    redirect_url = f"{settings.frontend_url}/callback?{params}"

    response = RedirectResponse(url=redirect_url)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
    )
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService()
    cookie = request.cookies.get("refresh_token")
    user, access_token, new_refresh = await auth_service.refresh_app_token(
        refresh_token=cookie, db=db
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
        ),
    )


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie("refresh_token")
    return None


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    channel_result = await db.execute(
        select(Channel).where(Channel.user_id == current_user.id).limit(1)
    )
    channel = channel_result.scalar_one_or_none()

    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        channel=ChannelSummary(
            id=str(channel.id),
            youtube_channel_id=channel.youtube_channel_id,
            channel_title=channel.channel_title,
            subscriber_count=channel.subscriber_count,
        ) if channel else None,
    )
