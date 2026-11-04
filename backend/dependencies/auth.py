import os
from collections.abc import Callable

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


load_dotenv()

JWT_ALGORITHM = "HS256"
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
) -> dict[str, str]:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    jwt_secret_key = os.getenv("JWT_SECRET_KEY")

    if not jwt_secret_key:
        raise HTTPException(
            status_code=500,
            detail="JWT secret key is not configured."
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            jwt_secret_key,
            algorithms=[JWT_ALGORITHM]
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    username = payload.get("sub")
    role = payload.get("role")

    if not isinstance(username, str) or not isinstance(role, str):
        raise HTTPException(
            status_code=401,
            detail="Invalid token claims.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return {
        "username": username,
        "role": role
    }


def require_roles(*allowed_roles: str) -> Callable:
    def role_checker(
        current_user: dict[str, str] = Depends(get_current_user)
    ) -> dict[str, str]:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action."
            )

        return current_user

    return role_checker
