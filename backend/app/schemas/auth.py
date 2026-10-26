from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class CurrentUserResponse(BaseModel):
    subject: str
    roles: list[str]
    permissions: list[str]
    regions: list[str]
    menus: list[str]
