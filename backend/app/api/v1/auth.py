"""
Auth API endpoints
"""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    create_password_reset_token,
    verify_password_reset_token,
)
from app.core.auth import get_current_user_id, get_current_user
from app.core.config import settings
from app.database.database import get_db
from app.models.otp import PasswordResetOTP
from app.models.user import User, UserRole
from app.models.subscription import (
    BillingCycle,
    PlanType,
    Subscription,
    SubscriptionStatus,
)
from app.schemas.user import (
    UserCreate, UserLogin, UserOut, Token, AdminCreate,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest,
    VerifyOtpRequest, VerifyOtpResponse,
)
from app.services.email_service import email_service
from app.services.token_blacklist import token_blacklist

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    existing_user = await db.execute(
        select(User).where(
            (User.email == user_data.email) | (User.username == user_data.username)
        )
    )
    if existing_user.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered",
        )

    role = user_data.role
    role_value = role.value if hasattr(role, "value") else role

    if role_value != UserRole.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'student'",
        )

    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        role=role_value,
        hashed_password=hashed_password,
    )
    db.add(new_user)
    await db.flush()

    # Every new student starts on the FREE plan.
    db.add(
        Subscription(
            user_id=new_user.id,
            plan_type=PlanType.FREE.value,
            billing_cycle=BillingCycle.NONE.value,
            status=SubscriptionStatus.ACTIVE.value,
        )
    )
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post(
    "/register-admin",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
async def register_admin(
    user_data: AdminCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new admin account.

    Only callers that provide the configured ``ADMIN_SECRET_KEY``
    are allowed to create admin users.
    """
    if user_data.admin_secret != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin registration key",
        )

    existing_user = await db.execute(
        select(User).where(
            (User.email == user_data.email) | (User.username == user_data.username)
        )
    )
    if existing_user.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered",
        )

    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        role=UserRole.ADMIN.value,
        is_verified=True,
        hashed_password=hashed_password,
    )
    db.add(new_user)
    await db.flush()

    # Admins also start on the FREE plan.
    db.add(
        Subscription(
            user_id=new_user.id,
            plan_type=PlanType.FREE.value,
            billing_cycle=BillingCycle.NONE.value,
            status=SubscriptionStatus.ACTIVE.value,
        )
    )
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user_result = await db.execute(
        select(User).where(
            (User.email == form_data.username) | (User.username == form_data.username)
        )
    )
    user = user_result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "type": "access"},
        expires_delta=timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "type": "refresh"},
        expires_delta=timedelta(minutes=settings.JWT_REFRESH_EXPIRE_MINUTES),
    )

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
):
    payload = await verify_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    new_access_token = create_access_token(
        data={"sub": str(user_id), "type": "access"},
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user_id), "type": "refresh"},
    )
    return Token(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    payload = await verify_access_token(token)
    if payload:
        exp = payload.get("exp")
        if exp:
            import time
            expires_in = max(1, int(exp - time.time()))
            await token_blacklist.add_token(token, expires_in)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserOut)
async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset email.

    Sends both a reset link and a 6-digit OTP (10 min) to the user's email
    if the account exists. Always returns success to prevent email enumeration.

    The email contains:
      - Option 1: reset link (JWT, 1 hour) → /reset-password?token=...
      - Option 2: OTP → /verify-otp → /reset-password?token=...
    """
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()

    if user:
        reset_token = create_password_reset_token(data={"sub": str(user.id)})
        frontend_url = (settings.FRONTEND_URL or "").strip() or (
            settings.ALLOWED_ORIGINS[0] if settings.ALLOWED_ORIGINS else "http://localhost:5173"
        )
        frontend_url = frontend_url.rstrip("/")

        # Generate 6-digit OTP, store hashed, expire in 10 minutes
        otp_plain = f"{secrets.randbelow(900000) + 100000:06d}"
        otp_hash = get_password_hash(otp_plain)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        # Invalidate previous OTPs for this email (mark used)
        prev = await db.execute(
            select(PasswordResetOTP).where(
                PasswordResetOTP.email == user.email,
                PasswordResetOTP.used == False  # noqa: E712
            )
        )
        for p in prev.scalars().all():
            p.used = True
        db.add(
            PasswordResetOTP(
                email=user.email,
                otp_hash=otp_hash,
                expires_at=expires_at,
                used=False,
            )
        )
        await db.flush()

        sent = await email_service.send_password_reset_email(
            to_email=user.email,
            reset_token=reset_token,
            frontend_url=frontend_url,
            otp=otp_plain,
        )
        if not sent:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "Password reset email not sent (check SMTP config). "
                "DEV RESET LINK for %s: %s/reset-password?token=%s | DEV OTP: %s (10 min)",
                user.email, frontend_url, reset_token, otp_plain,
            )
        else:
            # Also log OTP in DEBUG for local testing (remove in prod)
            if settings.DEBUG:
                import logging as _logging
                _logging.getLogger(__name__).info(
                    "DEV OTP for %s: %s (10 min) | link: %s/reset-password?token=%s",
                    user.email, otp_plain, frontend_url, reset_token,
                )
        await db.commit()

    return {"message": "If the email exists, a password reset link and OTP have been sent."}


@router.post("/verify-otp", response_model=VerifyOtpResponse)
async def verify_otp(
    request: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a 6-digit OTP and return a password reset token.

    The OTP is the same one sent alongside the reset link. On success,
    returns a JWT `reset_token` that can be used at
    `POST /reset-password` or `GET /reset-password?token=...`.

    This unifies the OTP and link flows: OTP → token → same ResetPassword UI.
    """
    email = request.email.lower().strip()
    otp = request.otp.strip()

    # Find latest unused, non-expired OTP for this email
    result = await db.execute(
        select(PasswordResetOTP)
        .where(PasswordResetOTP.email == email, PasswordResetOTP.used == False)  # noqa: E712
        .order_by(PasswordResetOTP.created_at.desc())
    )
    candidates = result.scalars().all()
    matched = None
    for cand in candidates:
        if cand.is_expired():
            continue
        # Argon2 verify (otp_plain vs hash)
        if verify_password(otp, cand.otp_hash):
            matched = cand
            break
        else:
            cand.attempts += 1
            # Optional: lock after 5 attempts
            if cand.attempts >= 5:
                cand.used = True
    await db.flush()
    if matched is None:
        # Check if any OTP expired vs wrong
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP. Please request a new one.",
        )

    # Mark OTP as used (single-use)
    matched.used = True
    await db.flush()

    # OTP is valid — issue a reset token for this email's user
    user_result = await db.execute(select(User).where(User.email == email))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    reset_token = create_password_reset_token(data={"sub": str(user.id)})
    await db.commit()
    return VerifyOtpResponse(reset_token=reset_token)


@router.post("/resend-otp")
async def resend_otp(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Resend OTP (and link) — convenience alias for forgot-password."""
    return await forgot_password(request, db)


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using a reset token.
    """
    payload = verify_password_reset_token(request.token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.hashed_password = get_password_hash(request.password)
    await db.commit()

    return {"message": "Password has been reset successfully"}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change password for authenticated user.
    """
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = get_password_hash(request.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}
