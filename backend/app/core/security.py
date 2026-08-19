# """
# Security and Authentication Utilities
# """
# from datetime import datetime, timedelta
# from typing import Optional

# from jose import jwt, JWTError
# from passlib.context import CryptContext

# from app.core.config import settings

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     return pwd_context.verify(plain_password, hashed_password)


# def get_password_hash(password: str) -> str:
#     return pwd_context.hash(password)


# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
#     to_encode.update({"exp": expire, "type": "access"})
#     return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_REFRESH_EXPIRE_MINUTES))
#     to_encode.update({"exp": expire, "type": "refresh"})
#     return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# def verify_access_token(token: str) -> Optional[dict]:
#     try:
#         payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
#         if payload.get("type") != "access":
#             return None
#         return payload
#     except JWTError:
#         return None


# def verify_refresh_token(token: str) -> Optional[dict]:
#     try:
#         payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
#         if payload.get("type") != "refresh":
#             return None
#         return payload
#     except JWTError:
#         return None


# """
# Security and Authentication Utilities
# """

# from datetime import datetime, timedelta, timezone
# from typing import Optional

# from jose import JWTError, jwt
# from passlib.context import CryptContext

# from app.core.config import settings


# # ============================================================
# # Password Hashing
# # ============================================================

# pwd_context = CryptContext(
#     schemes=["bcrypt"],
#     deprecated="auto"
# )


# def verify_password(
#     plain_password: str,
#     hashed_password: str
# ) -> bool:
#     """
#     Verify a plain-text password against its hashed version.
#     """

#     return pwd_context.verify(
#         plain_password,
#         hashed_password
#     )


# def get_password_hash(password: str) -> str:
#     """
#     Generate a secure hash for a password.
#     """

#     return pwd_context.hash(password)


# # ============================================================
# # Access Token
# # ============================================================

# def create_access_token(
#     data: dict,
#     expires_delta: Optional[timedelta] = None
# ) -> str:
#     """
#     Create a JWT access token.

#     Args:
#         data: Data to include in the JWT payload.
#         expires_delta: Optional custom expiration time.

#     Returns:
#         Encoded JWT access token.
#     """

#     to_encode = data.copy()

#     expire = datetime.now(timezone.utc) + (
#         expires_delta
#         or timedelta(
#             minutes=settings.JWT_EXPIRE_MINUTES
#         )
#     )

#     to_encode.update({
#         "exp": expire,
#         "type": "access"
#     })

#     return jwt.encode(
#         to_encode,
#         settings.SECRET_KEY,
#         algorithm=settings.JWT_ALGORITHM
#     )


# # ============================================================
# # Refresh Token
# # ============================================================

# def create_refresh_token(
#     data: dict,
#     expires_delta: Optional[timedelta] = None
# ) -> str:
#     """
#     Create a JWT refresh token.

#     Args:
#         data: Data to include in the JWT payload.
#         expires_delta: Optional custom expiration time.

#     Returns:
#         Encoded JWT refresh token.
#     """

#     to_encode = data.copy()

#     expire = datetime.now(timezone.utc) + (
#         expires_delta
#         or timedelta(
#             minutes=settings.JWT_REFRESH_EXPIRE_MINUTES
#         )
#     )

#     to_encode.update({
#         "exp": expire,
#         "type": "refresh"
#     })

#     return jwt.encode(
#         to_encode,
#         settings.SECRET_KEY,
#         algorithm=settings.JWT_ALGORITHM
#     )


# # ============================================================
# # Access Token Verification
# # ============================================================

# def verify_access_token(
#     token: str
# ) -> Optional[dict]:
#     """
#     Verify and decode an access token.

#     Returns:
#         JWT payload if valid, otherwise None.
#     """

#     try:
#         payload = jwt.decode(
#             token,
#             settings.SECRET_KEY,
#             algorithms=[settings.JWT_ALGORITHM]
#         )

#         if payload.get("type") != "access":
#             return None

#         return payload

#     except JWTError:
#         return None


# # ============================================================
# # Refresh Token Verification
# # ============================================================

# def verify_refresh_token(
#     token: str
# ) -> Optional[dict]:
#     """
#     Verify and decode a refresh token.

#     Returns:
#         JWT payload if valid, otherwise None.
#     """

#     try:
#         payload = jwt.decode(
#             token,
#             settings.SECRET_KEY,
#             algorithms=[settings.JWT_ALGORITHM]
#         )

#         if payload.get("type") != "refresh":
#             return None

#         return payload

#     except JWTError:
#         return None


"""
Security and Authentication Utilities
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError, VerificationError

from app.core.config import settings


# ============================================================
# Password Hashing
# ============================================================

password_hasher = PasswordHasher()


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """
    Verify a plain-text password against its hashed version.
    """

    try:
        password_hasher.verify(
            hashed_password,
            plain_password
        )
        return True

    except (InvalidHashError, VerifyMismatchError, VerificationError):
        return False


def get_password_hash(password: str) -> str:
    """
    Generate a secure Argon2 password hash.
    """

    return password_hasher.hash(password)


# ============================================================
# Access Token
# ============================================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to include in the JWT payload.
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT access token.
    """

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(
            minutes=settings.JWT_EXPIRE_MINUTES
        )
    )

    to_encode.update({
        "exp": expire,
        "type": "access"
    })

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


# ============================================================
# Refresh Token
# ============================================================

def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    """

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(
            minutes=settings.JWT_REFRESH_EXPIRE_MINUTES
        )
    )

    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


# ============================================================
# Access Token Verification
# ============================================================

def verify_access_token(
    token: str
) -> Optional[dict]:
    """
    Verify and decode an access token.

    Returns:
        JWT payload if valid, otherwise None.
    """

    try:
        from app.services.token_blacklist import token_blacklist
        import asyncio

        # Check if token is blacklisted
        is_blacklisted = asyncio.run(token_blacklist.is_blacklisted(token))
        if is_blacklisted:
            return None

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        if payload.get("type") != "access":
            return None

        return payload

    except JWTError:
        return None


# ============================================================
# Refresh Token Verification
# ============================================================

def verify_refresh_token(
    token: str
) -> Optional[dict]:
    """
    Verify and decode a refresh token.

    Returns:
        JWT payload if valid, otherwise None.
    """

    try:
        from app.services.token_blacklist import token_blacklist
        import asyncio

        # Check if token is blacklisted
        is_blacklisted = asyncio.run(token_blacklist.is_blacklisted(token))
        if is_blacklisted:
            return None

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        if payload.get("type") != "refresh":
            return None

        return payload

    except JWTError:
        return None


# ============================================================
# Password Reset Token
# ============================================================

def create_password_reset_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT password reset token.

    Args:
        data: Data to include in the JWT payload.
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT password reset token.
    """

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=60)
    )

    to_encode.update({
        "exp": expire,
        "type": "password_reset"
    })

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def verify_password_reset_token(
    token: str
) -> Optional[dict]:
    """
    Verify and decode a password reset token.

    Returns:
        JWT payload if valid, otherwise None.
    """

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        if payload.get("type") != "password_reset":
            return None

        return payload

    except JWTError:
        return None