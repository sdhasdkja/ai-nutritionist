"""用户 Pydantic 模式"""
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = Field(None, ge=1, le=120)
    gender: Optional[str] = None
    height: Optional[float] = Field(None, gt=0, lt=300)
    weight: Optional[float] = Field(None, gt=0, lt=500)


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=100)


class UserUpdate(BaseModel):
    """用户资料更新（不含用户名/邮箱）"""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = Field(None, ge=1, le=120)
    gender: Optional[str] = None
    height: Optional[float] = Field(None, gt=0, lt=300)
    weight: Optional[float] = Field(None, gt=0, lt=500)


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
