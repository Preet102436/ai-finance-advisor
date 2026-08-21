"""Pydantic request/response models for the auth and users routes."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
