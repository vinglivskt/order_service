from pydantic import BaseModel, EmailStr, Field


class SUserRegister(BaseModel):
    """Схема для регистрации пользователя."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class SUserRead(BaseModel):
    """Схема для чтения пользователя."""

    id: int
    email: EmailStr
    is_active: bool

    model_config = {"from_attributes": True}


class SToken(BaseModel):
    """Схема для токена."""

    access_token: str
    token_type: str = "bearer"
