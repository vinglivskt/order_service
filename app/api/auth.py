from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth.service import AuthApplicationService
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.domain.auth.exceptions import (
    InvalidCredentialsError,
    InvalidPasswordError,
    UserAlreadyExistsError,
)
from app.infrastructure.db.repositories.user_repository import SQLAlchemyUserRepository
from app.schemas.auth import SToken, SUserRead, SUserRegister

router = APIRouter(tags=["auth"])


def get_auth_service(db: AsyncSession) -> AuthApplicationService:
    return AuthApplicationService(
        user_repository=SQLAlchemyUserRepository(db),
    )


@router.post("/register/", response_model=SUserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def register_user(
    request: Request,
    payload: SUserRegister,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SUserRead:
    auth_service = get_auth_service(db)

    try:
        return await auth_service.register_user(payload)
    except InvalidPasswordError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль должен содержать буквы и цифры",
        ) from exc
    except UserAlreadyExistsError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь уже существует",
        ) from exc
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь уже существует",
        ) from exc


@router.post("/token/", response_model=SToken)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def login_for_access_token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SToken:
    auth_service = get_auth_service(db)

    try:
        return await auth_service.login(
            username=form_data.username,
            password=form_data.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
