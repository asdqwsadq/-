from sqlalchemy.orm import Session


def _paginate(query, page: int = 1, page_size: int = 19):
    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    items = [dict(r.__dict__) for r in rows]
    for item in items:
        item.pop("_sa_instance_state", None)
    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": total_pages}


def list_entities(db: Session, model, filters: list | None = None, sort_by: str = "id", sort_order: str = "desc", page: int = 1, page_size: int = 19):
    query = db.query(model)
    for cond in filters or []:
        if cond is not None:
            query = query.filter(cond)
    sort_column = getattr(model, sort_by, model.id)
    order_by = sort_column.asc() if sort_order.lower() == "asc" else sort_column.desc()
    return _paginate(query.order_by(order_by), page, page_size)


def get_entity(db: Session, model, item_id: int):
    return db.query(model).filter(model.id == item_id).first()


def create_entity(db: Session, model, payload):
    obj = model(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_entity(db: Session, obj, payload):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_entity(db: Session, obj):
    db.delete(obj)
    db.commit()
