from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import SToken, SUserRead, SUserRegister

router = APIRouter(tags=["auth"])


@router.post("/register/", response_model=SUserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def register_user(
    request: Request,
    payload: SUserRegister,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SUserRead:
    """Регистрация пользователя (email,
    пароль)"""

    if not any(ch.isdigit() for ch in payload.password) or not any(ch.isalpha() for ch in payload.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пароль должен содержать буквы и цифры")

    result = await db.execute(select(User).where(User.email == payload.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Пользователь уже существует")

    user = User(email=payload.email, hashed_password=get_password_hash(payload.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return SUserRead.model_validate(user)


@router.post("/token/", response_model=SToken)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def login_for_access_token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SToken:
    """Получение JWT-токена (OAuth2)"""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=str(user.id), expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return SToken(access_token=access_token)
