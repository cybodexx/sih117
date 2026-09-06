from __future__ import annotations

from pydantic import BaseModel, Field


class AuthLogin(BaseModel):
    username: str
    password: str


class RegisterUser(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = ""
    role: str = "VIEWER"
    clearance_level: int = 0
    departments: list[str] = []


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900
    user: UserRead


class UserRead(BaseModel):
    id: str
    username: str
    full_name: str
    role: str
    clearance_level: int
    departments: list[str]
    created_at: str


class RefreshRequest(BaseModel):
    refresh_token: str
