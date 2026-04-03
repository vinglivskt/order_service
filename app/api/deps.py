from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.observability.log_context import set_request_context
from app.db.session import get_db
from app.models.user import User
from app.services.auth_cache_service import AuthCacheService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token/")


async def get_redis(request: Request) -> Redis:
    return request.app.state.redis


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> User:
    """Получает текущего пользователя по JWT токену.

    На cache-hit проверяет `is_active` в Redis и не ходит в БД.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
        user_id = int(subject)
    except Exception as exc:
        raise credentials_exception from exc

    cache_service = AuthCacheService(redis)
    cached_user = await cache_service.get_user(user_id)
    if cached_user is not None:
        if not cached_user.is_active:
            raise credentials_exception

        # Нам критичен минимум полей для текущих роутеров (это `id`).
        user = User(
            id=cached_user.id, email="", hashed_password="", is_active=cached_user.is_active
        )
        set_request_context(user_id=str(user.id))
        return user

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise credentials_exception

    await cache_service.set_user(user.id, user.is_active)
    set_request_context(user_id=str(user.id))
    return user
