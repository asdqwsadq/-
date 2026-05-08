from sqlalchemy.orm import Session

from app.models.entities import OperationLog


def list_logs_service(db: Session, page: int = 1, page_size: int = 10):
    query = db.query(OperationLog).order_by(OperationLog.id.desc())
    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    items = [dict(r.__dict__) for r in rows]
    for item in items:
        item.pop("_sa_instance_state", None)
    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": total_pages}
