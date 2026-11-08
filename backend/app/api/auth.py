import asyncio
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core import audit
from app.core.config import get_settings
from app.core.security import (
    create_reset_token,
    create_token,
    decode_token,
    hash_password,
    reset_token_matches,
    verify_password,
)
from app.db.models import RefreshToken, User
from app.db.session import get_db
from app.integrations.factory import get_email_sender

router = APIRouter(prefix="/auth", tags=["auth"])
_DUMMY_HASH = hash_password("timing-equalisation-only")


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
    token_type: str = "bearer"  # noqa: S105


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
    user = User(email=body.email.lower(), password_hash=await asyncio.to_thread(hash_password, body.password), language=body.language)
    db.add(user)
    await db.commit()
    await audit.record(db, user.id, "auth.register")
    return await _issue(db, user)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    # always run one bcrypt verification so response time does not reveal whether the email exists
    stored = user.password_hash if user and not user.deleted_at else _DUMMY_HASH
    valid = await asyncio.to_thread(verify_password, body.password, stored)
    s = get_settings()
    now = datetime.now(UTC)
    if user and not user.deleted_at:
        until = user.locked_until if user.locked_until is None or user.locked_until.tzinfo else user.locked_until.replace(tzinfo=UTC)
        if until and until > now:  # locked: even the right password is refused until the window ends
            await audit.record(db, user.id, "auth.login_blocked_locked")
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, {"code": "account_locked", "message": f"Too many failed attempts. Try again in {max(1, int((until - now).total_seconds() // 60) + 1)} minutes, or reset your password."})
    if not user or user.deleted_at or not valid:
        if user and not user.deleted_at:
            user.failed_logins = (user.failed_logins or 0) + 1
            if user.failed_logins >= s.lockout_threshold:
                user.locked_until = now + timedelta(minutes=s.lockout_minutes)
                user.failed_logins = 0
                await audit.record(db, user.id, "auth.account_locked")
            await db.commit()
        await audit.record(db, "anonymous", "auth.login_failed")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    user.failed_logins, user.locked_until = 0, None
    await db.commit()
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


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=20, max_length=2000)
    password: str = Field(min_length=10, max_length=128)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)


_RESET_MAIL = {
    "en": (
        "Reset your Red Tape Navigator password",
        "Use this link to choose a new password (valid {m} minutes):\n{url}\n\n"
        "If you did not ask for this, ignore this email; your password is unchanged.",
    ),
    "hi": (
        "Red Tape Navigator पासवर्ड रीसेट करें",
        "नया पासवर्ड चुनने के लिए यह लिंक खोलें ({m} मिनट तक मान्य):\n{url}\n\n"
        "यदि आपने यह अनुरोध नहीं किया, तो इस ईमेल को अनदेखा करें; आपका पासवर्ड नहीं बदला है।",
    ),
    "bn": (
        "Red Tape Navigator পাসওয়ার্ড রিসেট করুন",
        "নতুন পাসওয়ার্ড বেছে নিতে এই লিঙ্কটি খুলুন ({m} মিনিট বৈধ):\n{url}\n\n"
        "আপনি অনুরোধ না করে থাকলে এই ইমেল উপেক্ষা করুন; আপনার পাসওয়ার্ড বদলায়নি।",
    ),
}

async def _send_reset_email(email: str, language: str, token: str) -> None:
    s = get_settings()
    subject, body = _RESET_MAIL.get(language, _RESET_MAIL["en"])
    url = f"{s.web_base_url.rstrip('/')}/{language if language in _RESET_MAIL else 'en'}/reset?token={token}"
    await get_email_sender().send(email, body.format(m=s.reset_token_minutes, url=url), subject)


async def _revoke_all(db: AsyncSession, user_id: str) -> None:
    for t in (await db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id))).scalars():
        t.revoked = True
    await db.commit()


@router.post("/forgot", status_code=202)
async def forgot_password(body: ForgotIn, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Always answers 202 so the endpoint cannot be used to discover which emails are registered."""
    user = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if user and not user.deleted_at:
        background.add_task(_send_reset_email, user.email, user.language, create_reset_token(user.id, user.password_hash))
        await audit.record(db, user.id, "auth.reset_requested")
    return {"status": "ok"}


@router.post("/reset")
async def reset_password(body: ResetIn, db: AsyncSession = Depends(get_db)):
    bad = HTTPException(status.HTTP_400_BAD_REQUEST, "Reset link is invalid or has expired")
    try:
        data = decode_token(body.token, "reset")
    except jwt.PyJWTError as exc:
        raise bad from exc
    user = await db.get(User, data["sub"])
    if user is None or user.deleted_at or not reset_token_matches(data, user.password_hash):
        raise bad
    user.password_hash = await asyncio.to_thread(hash_password, body.password)
    user.failed_logins, user.locked_until = 0, None
    await db.commit()
    await _revoke_all(db, user.id)  # sign out every existing session
    await audit.record(db, user.id, "auth.password_reset")
    return {"status": "ok"}


@router.post("/change-password", response_model=TokenOut)
async def change_password(body: ChangePasswordIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if not await asyncio.to_thread(verify_password, body.current_password, user.password_hash):
        await audit.record(db, user.id, "auth.change_password_failed")
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Current password is incorrect")
    user.password_hash = await asyncio.to_thread(hash_password, body.new_password)
    await db.commit()
    await _revoke_all(db, user.id)
    await audit.record(db, user.id, "auth.password_changed")
    return await _issue(db, user)
