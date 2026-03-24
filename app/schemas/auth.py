from pydantic import BaseModel, Field


EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"


class UserRegister(BaseModel):
    email: str = Field(..., min_length=5, max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=200)


class UserLogin(BaseModel):
    email: str = Field(..., min_length=5, max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(patient|nurse|doctor|admin)$")


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int


class DeactivateResponse(BaseModel):
    id: str
    email: str
    is_active: bool

    model_config = {"from_attributes": True}
