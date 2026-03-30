from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.common.ports import UserRepositoryPort
from app.domain.users.entities import User
from app.models.user import User as UserModel


class SQLAlchemyUserRepository(UserRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        orm_user = result.scalar_one_or_none()
        if orm_user is None:
            return None
        return self._to_domain(orm_user)

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user_id))
        orm_user = result.scalar_one_or_none()
        if orm_user is None:
            return None
        return self._to_domain(orm_user)

    async def add(self, user: User) -> User:
        orm_user = self._to_orm(user)
        self._session.add(orm_user)
        await self._session.flush()
        # ensure the ORM object has DB defaults / generated PKs populated
        await self._session.commit()
        await self._session.refresh(orm_user)
        return self._to_domain(orm_user)

    async def create(self, email: str, hashed_password: str) -> User:
        """
        Convenience creator that persists a new User model and returns domain user.
        Commits and refreshes to ensure DB-generated fields (like id) are populated.
        """
        orm = UserModel(email=email, hashed_password=hashed_password, is_active=True)
        self._session.add(orm)
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(orm)
        return self._to_domain(orm)

    @staticmethod
    def _to_domain(orm_user: UserModel) -> User:
        return User(
            id=orm_user.id,
            email=orm_user.email,
            hashed_password=orm_user.hashed_password,
            is_active=orm_user.is_active,
        )

    @staticmethod
    def _to_orm(user: User) -> UserModel:
        kwargs = {
            "email": user.email,
            "hashed_password": user.hashed_password,
            "is_active": user.is_active,
        }
        if user.id:
            kwargs["id"] = user.id
        return UserModel(**kwargs)
