from sqlalchemy.orm import Session

from app.models.entities import UserAccount


def get_user_by_username(db: Session, username: str):
    return db.query(UserAccount).filter(UserAccount.username == username).first()


def get_user_by_id(db: Session, item_id: int):
    return db.query(UserAccount).filter(UserAccount.id == item_id).first()


def list_users(
    db: Session,
    username: str | None,
    role: str | None,
    is_active: bool | None,
    sort_by: str,
    sort_order: str,
    page: int = 1,
    page_size: int = 10,
):
    query = db.query(UserAccount)
    if username:
        query = query.filter(UserAccount.username.like(f"%{username}%"))
    if role:
        query = query.filter(UserAccount.role == role)
    if is_active is not None:
        query = query.filter(UserAccount.is_active == is_active)
    sort_column = getattr(UserAccount, sort_by, UserAccount.id)
    order_by = sort_column.asc() if sort_order.lower() == "asc" else sort_column.desc()
    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    rows = query.order_by(order_by).offset((page - 1) * page_size).limit(page_size).all()
    items = [dict(r.__dict__) for r in rows]
    for item in items:
        item.pop("_sa_instance_state", None)
    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": total_pages}
