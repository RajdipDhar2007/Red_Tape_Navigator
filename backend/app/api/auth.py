from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core import audit
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.db.models import RefreshToken, User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    language: str = Field(default="en", pattern="^(en|bn|hi)$")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


async def _issue(db: AsyncSession, user: User) -> TokenOut:
    access, _, _ = create_token(user.id, user.role, "access")
    refresh, jti, exp = create_token(user.id, user.role, "refresh")
    db.add(RefreshToken(jti=jti, user_id=user.id, expires_at=exp))
    await db.commit()
    return TokenOut(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    # self-registration is always a citizen; elevated roles are granted by admins only
    user = User(email=body.email.lower(), password_hash=hash_password(body.password), language=body.language)
    db.add(user)
    await db.commit()
    await audit.record(db, user.id, "auth.register")
    return await _issue(db, user)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if not user or user.deleted_at or not verify_password(body.password, user.password_hash):
        await audit.record(db, "anonymous", "auth.login_failed")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    await audit.record(db, user.id, "auth.login")
    return await _issue(db, user)


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, db: AsyncSession = Depends(get_db)):
    """Rotating refresh tokens; reuse of a revoked token revokes the whole family for that user."""
    try:
        data = decode_token(body.refresh_token, "refresh")
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from exc
    row = await db.get(RefreshToken, data["jti"])
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown refresh token")
    if row.revoked:
        for t in (await db.execute(select(RefreshToken).where(RefreshToken.user_id == row.user_id))).scalars():
            t.revoked = True
        await db.commit()
        await audit.record(db, row.user_id, "auth.refresh_reuse_detected")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token reuse detected")
    exp = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
    if exp < datetime.now(UTC):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expired")
    row.revoked = True
    user = await db.get(User, row.user_id)
    if user is None or user.deleted_at:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    await db.commit()
    return await _issue(db, user)


@router.get("/me")
async def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "role": user.role, "language": user.language}
