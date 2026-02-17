from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database import get_db
from src.app.models.user import User
from src.app.services.auth import decode_access_token, get_user_by_id


class AuthRedirect(Exception):
    """Raised when user needs to be redirected to login page."""
    pass


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise AuthRedirect()
    user_id = decode_access_token(token)
    if user_id is None:
        raise AuthRedirect()
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise AuthRedirect()
    if not user.is_active:
        raise AuthRedirect()
    return user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    user_id = decode_access_token(token)
    if user_id is None:
        return None
    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        return None
    return user
