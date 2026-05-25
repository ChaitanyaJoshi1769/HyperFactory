"""Authentication schemas"""

from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserBase(BaseModel):
    """Base user fields"""
    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    full_name: Optional[str] = None
    organization: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema"""
    password: str = Field(..., min_length=8, max_length=255)


class UserRead(UserBase):
    """User read schema"""
    id: UUID
    is_active: bool
    is_admin: bool
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update schema"""
    full_name: Optional[str] = None
    organization: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8, max_length=255)


class UserLogin(BaseModel):
    """User login schema"""
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class TokenData(BaseModel):
    """Token payload data"""
    user_id: str
    username: str
    email: str
    role: str
    is_admin: bool


class APIKeyCreate(BaseModel):
    """API key creation schema"""
    name: str = Field(..., min_length=1, max_length=255)
    expires_at: Optional[datetime] = None


class APIKeyRead(BaseModel):
    """API key read schema"""
    id: UUID
    name: str
    is_active: bool
    last_used: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True
