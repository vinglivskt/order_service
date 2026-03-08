from pydantic import BaseModel, EmailStr, Field


class SUserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class SUserRead(BaseModel):
    id: int
    email: EmailStr
    is_active: bool

    model_config = {"from_attributes": True}


class SToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
