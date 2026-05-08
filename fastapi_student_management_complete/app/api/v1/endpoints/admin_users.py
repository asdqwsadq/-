from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.database import get_db
from app.schemas.entities import UserAccountCreate, UserAccountPageResponse, UserAccountResponse, UserAccountUpdate
from app.services.admin_user_service import (
    create_admin_user_service,
    delete_admin_user_service,
    get_admin_user_service,
    list_admin_users_service,
    update_admin_user_service,
)

router = APIRouter(prefix="/admin/users", tags=["admin_users"])


@router.get("", response_model=UserAccountPageResponse)
def list_admin_users(
    username: str | None = Query(default=None),
    role: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    sort_by: str = Query(default="id"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
    _: dict[str, str] = Depends(require_admin),
):
    return list_admin_users_service(db, username, role, is_active, sort_by, sort_order, page, page_size)


@router.post("", response_model=UserAccountResponse, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    payload: UserAccountCreate,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_admin),
):
    return create_admin_user_service(db, payload, user)


@router.get("/{item_id}", response_model=UserAccountResponse)
def get_admin_user(item_id: int, db: Session = Depends(get_db), _: dict[str, str] = Depends(require_admin)):
    return get_admin_user_service(db, item_id)


@router.put("/{item_id}", response_model=UserAccountResponse)
def update_admin_user(
    item_id: int,
    payload: UserAccountUpdate,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_admin),
):
    return update_admin_user_service(db, item_id, payload, user)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_user(item_id: int, db: Session = Depends(get_db), user: dict[str, str] = Depends(require_admin)):
    delete_admin_user_service(db, item_id, user)
