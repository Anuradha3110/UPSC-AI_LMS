"""
users collection (§07). Roles match §03's personas exactly — keep the two
in sync if a new role is ever added.
"""
from enum import Enum

from pydantic import BaseModel, EmailStr


class UserRole(str, Enum):
    aspirant = "aspirant"
    mentor = "mentor"
    content_editor = "content_editor"
    admin = "admin"


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.aspirant
    optional_subject: str | None = None


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: UserRole
    optional_subject: str | None = None


class UserInDB(UserOut):
    password_hash: str
