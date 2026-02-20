import os
import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthUser:
    role: str


def _load_token_roles() -> list[tuple[str, str]]:
    """
    Carga tokens desde variables de entorno.
    Formatos soportados:
    - ADMIN_API_TOKEN=<token_admin>
    - AUTH_TOKENS=<token1>:<rol1>,<token2>:<rol2>
    """
    token_roles: list[tuple[str, str]] = []

    admin_token = os.getenv("ADMIN_API_TOKEN", "").strip()
    if admin_token:
        token_roles.append((admin_token, "admin"))

    raw_auth_tokens = os.getenv("AUTH_TOKENS", "").strip()
    if raw_auth_tokens:
        for pair in raw_auth_tokens.split(","):
            token_and_role = pair.strip()
            if not token_and_role or ":" not in token_and_role:
                continue
            token, role = token_and_role.split(":", 1)
            token = token.strip()
            role = role.strip().lower()
            if token and role:
                token_roles.append((token, role))

    return token_roles


def _resolve_user_from_token(token: str) -> AuthUser | None:
    for expected_token, role in _load_token_roles():
        if secrets.compare_digest(token, expected_token):
            return AuthUser(role=role)
    return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
        )

    user = _resolve_user_from_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )

    return user


async def require_admin_user(
    user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes. Se requiere rol admin",
        )
    return user
