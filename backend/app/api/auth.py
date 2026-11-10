import asyncio
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core import audit, totp
from app.core.config import get_settings
from app.core.crypto import decrypt, encrypt
from app.core.security import (
    create_reset_token,
    create_token,
    create_verify_token,
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
    otp: str | None = Field(default=None, max_length=32)  # authenticator code or a recovery code


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
async def register(body: RegisterIn, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    # self-registration is always a citizen; elevated roles are granted by admins only
    user = User(email=body.email.lower(), password_hash=await asyncio.to_thread(hash_password, body.password), language=body.language)
    db.add(user)
    await db.commit()
    await audit.record(db, user.id, "auth.register")
    background.add_task(_send_verify_email, user.email, user.language, create_verify_token(user.id, user.email))
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
    otp_ok = True
    if valid and user and not user.deleted_at and user.totp_enabled:
        if not body.otp:  # right password, second factor still needed: not a failed attempt
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, {"code": "otp_required", "message": "Enter the 6-digit code from your authenticator app, or a recovery code."})
        otp_ok = _consume_second_factor(user, body.otp)
    if not user or user.deleted_at or not valid or not otp_ok:
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
    return {"id": user.id, "email": user.email, "role": user.role, "language": user.language,
            "email_verified": user.email_verified_at is not None, "two_factor": bool(user.totp_enabled)}


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

_VERIFY_MAIL = {
    "en": ("Confirm your email for Red Tape Navigator", "Open this link to confirm your email address (valid 48 hours):\n{url}\n\nIf you did not create an account, ignore this email."),
    "hi": ("Red Tape Navigator के लिए अपना ईमेल पुष्ट करें", "अपना ईमेल पता पुष्ट करने के लिए यह लिंक खोलें (48 घंटे तक मान्य):\n{url}\n\nयदि आपने खाता नहीं बनाया, तो इस ईमेल को अनदेखा करें।"),
    "bn": ("Red Tape Navigator-এর জন্য আপনার ইমেল নিশ্চিত করুন", "আপনার ইমেল ঠিকানা নিশ্চিত করতে এই লিঙ্কটি খুলুন (৪৮ ঘণ্টা বৈধ):\n{url}\n\nআপনি অ্যাকাউন্ট না খুলে থাকলে এই ইমেল উপেক্ষা করুন।"),
}


async def _send_verify_email(email: str, language: str, token: str) -> None:
    """Goes only to the address being verified, never to anyone else."""
    s = get_settings()
    subject, body = _VERIFY_MAIL.get(language, _VERIFY_MAIL["en"])
    url = f"{s.web_base_url.rstrip('/')}/{language if language in _VERIFY_MAIL else 'en'}/verify-email?token={token}"
    await get_email_sender().send(email, body.format(url=url), subject)


def _consume_second_factor(user: User, code: str) -> bool:
    """Accept a current authenticator code (once only) or an unused recovery code (burned on use). Mutates ``user``; caller commits."""
    if user.totp_secret:
        step = totp.verify(decrypt(user.totp_secret), code, user.totp_last_step or 0)
        if step is not None:
            user.totp_last_step = step
            return True
    h = totp.hash_recovery(code)
    if h in (user.recovery_hashes or []):
        user.recovery_hashes = [x for x in user.recovery_hashes if x != h]
        return True
    return False


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


class TokenIn(BaseModel):
    token: str = Field(min_length=20, max_length=2000)


@router.post("/verify-email/send", status_code=202)
async def resend_verification(background: BackgroundTasks, user: User = Depends(current_user)):
    if user.email_verified_at is None:
        background.add_task(_send_verify_email, user.email, user.language, create_verify_token(user.id, user.email))
    return {"status": "ok"}


@router.post("/verify-email")
async def verify_email(body: TokenIn, db: AsyncSession = Depends(get_db)):
    bad = HTTPException(status.HTTP_400_BAD_REQUEST, "Verification link is invalid or has expired")
    try:
        data = decode_token(body.token, "verify")
    except jwt.PyJWTError as exc:
        raise bad from exc
    user = await db.get(User, data["sub"])
    if user is None or user.deleted_at or user.email != data.get("em"):
        raise bad
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(UTC)
        await db.commit()
        await audit.record(db, user.id, "auth.email_verified")
    return {"status": "verified"}


class CodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=32)


class DisableIn(CodeIn):
    password: str


@router.post("/2fa/setup")
async def two_factor_setup(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    """Starts enrolment. Two-factor is not active until a code from the app is confirmed with /2fa/enable."""
    if user.totp_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "Two-factor sign-in is already on")
    secret = totp.new_secret()
    user.totp_secret = encrypt(secret)
    await db.commit()
    return {"secret": secret, "otpauth_uri": totp.otpauth_uri(secret, user.email)}


@router.post("/2fa/enable")
async def two_factor_enable(body: CodeIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if user.totp_enabled or not user.totp_secret:
        raise HTTPException(status.HTTP_409_CONFLICT, "Start with /auth/2fa/setup")
    step = totp.verify(decrypt(user.totp_secret), body.code, user.totp_last_step or 0)
    if step is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That code is not correct. Check the time on your phone and try again.")
    codes = totp.new_recovery_codes()
    user.totp_enabled, user.totp_last_step = True, step
    user.recovery_hashes = [totp.hash_recovery(c) for c in codes]
    await db.commit()
    await audit.record(db, user.id, "auth.2fa_enabled")
    return {"enabled": True, "recovery_codes": codes}  # shown once; only hashes are kept


@router.post("/2fa/disable")
async def two_factor_disable(body: DisableIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if not user.totp_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "Two-factor sign-in is not on")
    uid = user.id  # read before a rollback expires the instance
    if not await asyncio.to_thread(verify_password, body.password, user.password_hash) or not _consume_second_factor(user, body.code):
        await db.rollback()
        await audit.record(db, uid, "auth.2fa_disable_failed")
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Password or code is incorrect")
    user.totp_enabled, user.totp_secret, user.totp_last_step, user.recovery_hashes = False, None, 0, []
    await db.commit()
    await audit.record(db, user.id, "auth.2fa_disabled")
    return {"enabled": False}
