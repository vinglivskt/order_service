from datetime import timedelta

from sqlalchemy.exc import IntegrityError

from app.application.common.ports import UserRepositoryPort
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.domain.auth.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.domain.auth.validators import validate_password
from app.domain.users.entities import User
from app.schemas.auth import SToken, SUserRead, SUserRegister


class AuthApplicationService:
    """Application service for authentication use cases."""

    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self._user_repository = user_repository

    @staticmethod
    def _to_read_model(user: User) -> SUserRead:
        return SUserRead(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
        )

    async def register_user(self, payload: SUserRegister) -> SUserRead:
        validate_password(payload.password)

        existing_user = await self._user_repository.get_by_email(payload.email)
        if existing_user is not None:
            raise UserAlreadyExistsError("Пользователь уже существует")

        user = User(
            id=0,
            email=payload.email,
            hashed_password=get_password_hash(payload.password),
            is_active=True,
        )

        try:
            created_user = await self._user_repository.add(user)
        except IntegrityError as exc:
            raise UserAlreadyExistsError("Пользователь уже существует") from exc

        return self._to_read_model(created_user)

    async def login(self, username: str, password: str) -> SToken:
        user = await self._user_repository.get_by_email(username)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Неверный логин или пароль")

        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return SToken(access_token=access_token)
