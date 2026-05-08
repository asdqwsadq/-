import os
import secrets
import hashlib
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.models.entities import UserAccount

TOKENS: dict[str, dict[str, str]] = {}


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _verify_password(raw_password: str, stored_password: str) -> bool:
    # Backward compatibility for old plaintext records.
    return stored_password == raw_password or stored_password == _hash_password(raw_password)


def ensure_default_accounts(db: Session):
    # Only bootstrap one admin account when user table is empty.
    if db.query(UserAccount).count() > 0:
        return
    username = os.getenv("APP_ADMIN_USERNAME", "admin")
    password = os.getenv("APP_ADMIN_PASSWORD", "123456")
    db.add(UserAccount(username=username, password=_hash_password(password), role="admin", is_active=True))
    db.commit()


def login(db: Session, username: str, password: str) -> Optional[dict[str, str]]:
    user = db.query(UserAccount).filter(UserAccount.username == username).first()
    if not user or not user.is_active or not _verify_password(password, user.password):
        return None
    if user.password == password:
        user.password = _hash_password(password)
        db.commit()

    token = secrets.token_hex(24)
    TOKENS[token] = {"username": username, "role": user.role}
    return {"token": token, "username": username, "role": user.role}


def require_login(
    authorization: Optional[str] = Header(default=None),
    x_token: Optional[str] = Header(default=None),
) -> dict[str, str]:
    token = x_token
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token or token not in TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
        )
    return TOKENS[token]


def require_teacher(user: dict[str, str] = Depends(require_login)):
    if not user or user.get("role") not in ("teacher", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前账号无写入权限",
        )
    return user


def require_admin(user: dict[str, str] = Depends(require_login)):
    if not user or user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可访问",
        )
    return user
