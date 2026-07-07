from pydantic import BaseModel, Field
from typing import Optional

class DonorRegister(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=1)
    phone: str
    city: str
    state: str

class NGORegister(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    org: str = Field(..., min_length=1)
    registrationNumber: str
    contactPerson: str
    phone: str
    address: str
    city: str
    state: str
    focusAreas: str
    mission: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    name: str
    org: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    address: Optional[str] = None
    contactPerson: Optional[str] = None
    registrationNumber: Optional[str] = None
    focusAreas: Optional[str] = None
    mission: Optional[str] = None
    tenantId: Optional[int] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
