import logging
from datetime import datetime, timedelta, timezone
import os

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pwdlib import PasswordHash
from sqlalchemy import text

from database.connection import engine
from dependencies.auth import get_current_user
from schemas.auth import LoginRequest, PasswordChangeRequest


load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

password_hash = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


@router.post("/login")
def login(credentials: LoginRequest):
    jwt_secret_key = os.getenv("JWT_SECRET_KEY")

    if not jwt_secret_key:
        raise HTTPException(
            status_code=500,
            detail="JWT secret key is not configured."
        )

    try:
        with engine.connect() as connection:
            account = connection.execute(
                text("""
                    SELECT username,
                           password_hash,
                           role,
                           is_active,
                           must_change_password
                    FROM user_accounts
                    WHERE username = :username
                """),
                {"username": credentials.username}
            ).mappings().first()

        if account is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password."
            )

        if not account["is_active"]:
            raise HTTPException(
                status_code=403,
                detail="User account is inactive."
            )

        if not password_hash.verify(
            credentials.password,
            account["password_hash"]
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password."
            )

        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
        token = jwt.encode(
            {
                "sub": account["username"],
                "role": account["role"],
                "must_change_password": bool(account["must_change_password"]),
                "exp": expires_at
            },
            jwt_secret_key,
            algorithm=JWT_ALGORITHM
        )

        with engine.begin() as connection:
            connection.execute(
                text("""
                    UPDATE user_accounts
                    SET last_login = :last_login
                    WHERE username = :username
                """),
                {
                    "last_login": datetime.now(timezone.utc),
                    "username": account["username"]
                }
            )

        return {
            "access_token": token,
            "token_type": "bearer",
            "username": account["username"],
            "role": account["role"],
            "must_change_password": bool(account["must_change_password"])
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected login error.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )


@router.post("/change-password")
def change_password(
    request: PasswordChangeRequest,
    current_user: dict[str, str] = Depends(get_current_user)
):
    try:
        with engine.begin() as connection:
            account = connection.execute(
                text("""
                    SELECT password_hash
                    FROM user_accounts
                    WHERE username = :username
                    FOR UPDATE
                """),
                {"username": current_user["username"]}
            ).mappings().first()

            if account is None:
                raise HTTPException(
                    status_code=401,
                    detail="Authenticated account not found."
                )

            if not password_hash.verify(
                request.current_password,
                account["password_hash"]
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Current password is incorrect."
                )

            connection.execute(
                text("""
                    UPDATE user_accounts
                    SET password_hash = :password_hash,
                        must_change_password = FALSE
                    WHERE username = :username
                """),
                {
                    "password_hash": password_hash.hash(request.new_password),
                    "username": current_user["username"]
                }
            )

            return {
                "message": "Password changed successfully."
            }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected password change error.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error."
        )
