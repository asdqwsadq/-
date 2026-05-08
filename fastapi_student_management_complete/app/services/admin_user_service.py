from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.audit import write_log
from app.core.auth import _hash_password
from app.models.entities import UserAccount
from app.repositories.user_repository import get_user_by_id, get_user_by_username, list_users


def list_admin_users_service(
    db: Session, username: str | None, role: str | None, is_active: bool | None, sort_by: str, sort_order: str,
    page: int = 1, page_size: int = 10,
):
    return list_users(db, username, role, is_active, sort_by, sort_order, page=page, page_size=page_size)


def create_admin_user_service(db: Session, payload, operator: dict[str, str]):
    exists = get_user_by_username(db, payload.username)
    if exists:
        raise HTTPException(status_code=400, detail="账号已存在")
    data = payload.model_dump()
    data["password"] = _hash_password(data["password"])
    obj = UserAccount(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    write_log(db, operator["username"], operator["role"], "admin_users", "create", obj.id, f"新建账号 {obj.username}")
    return obj


def get_admin_user_service(db: Session, item_id: int):
    obj = get_user_by_id(db, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="账号不存在")
    return obj


def update_admin_user_service(db: Session, item_id: int, payload, operator: dict[str, str]):
    obj = get_user_by_id(db, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="账号不存在")
    if payload.username and payload.username != obj.username:
        duplicate = get_user_by_username(db, payload.username)
        if duplicate:
            raise HTTPException(status_code=400, detail="账号已存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "password":
            value = _hash_password(value)
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    write_log(db, operator["username"], operator["role"], "admin_users", "update", obj.id, f"更新账号 {obj.username}")
    return obj


def delete_admin_user_service(db: Session, item_id: int, operator: dict[str, str]):
    obj = get_user_by_id(db, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="账号不存在")
    write_log(db, operator["username"], operator["role"], "admin_users", "delete", obj.id, f"删除账号 {obj.username}")
    db.delete(obj)
    db.commit()
