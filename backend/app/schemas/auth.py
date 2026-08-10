"""认证相关 Schema。"""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    email: EmailStr | None = None
    phone: str | None = None
    password: str = Field(min_length=8, max_length=128)

    model_config = {"json_schema_extra": {"example": {"username": "xiaozhou", "email": "x@qq.com", "password": "pass1234"}}}


class LoginRequest(BaseModel):
    account: str  # 邮箱或手机号
    password: str

    model_config = {"json_schema_extra": {"example": {"account": "x@qq.com", "password": "pass1234"}}}


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None = None
    phone: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
