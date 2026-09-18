"""
MOD-01 — Identity & Access. Minimal register/login; role-based gating
happens in dependencies other modules import from here later.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import UserCreate, UserOut

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


def _to_user_out(doc: dict) -> UserOut:
    return UserOut(
        id=str(doc["_id"]),
        name=doc["name"],
        email=doc["email"],
        role=doc["role"],
        optional_subject=doc.get("optional_subject"),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    if await db.users.find_one({"email": payload.email}):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    doc = {
        "name": payload.name,
        "email": payload.email,
        "role": payload.role.value,
        "optional_subject": payload.optional_subject,
        "password_hash": hash_password(payload.password),
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id

    token = create_access_token(subject=str(result.inserted_id), role=doc["role"])
    return TokenResponse(access_token=token, user=_to_user_out(doc))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    doc = await db.users.find_one({"email": payload.email})
    if not doc or not verify_password(payload.password, doc["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    token = create_access_token(subject=str(doc["_id"]), role=doc["role"])
    return TokenResponse(access_token=token, user=_to_user_out(doc))
