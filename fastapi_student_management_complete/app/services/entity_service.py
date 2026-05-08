from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.audit import write_log
from app.repositories.entity_repository import create_entity, delete_entity, get_entity, list_entities, update_entity


def list_with_filters(db: Session, model, filters: list | None, sort_by: str, sort_order: str, page: int = 1, page_size: int = 19):
    return list_entities(db, model, filters, sort_by=sort_by, sort_order=sort_order, page=page, page_size=page_size)


def get_by_id(db: Session, model, item_id: int, not_found_msg: str):
    obj = get_entity(db, model, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail=not_found_msg)
    return obj


def create_with_log(db: Session, model, payload, user: dict[str, str], module: str, detail_field: str):
    obj = create_entity(db, model, payload)
    write_log(db, user["username"], user["role"], module, "create", obj.id, str(getattr(obj, detail_field, obj.id)))
    return obj


def update_with_log(db: Session, obj, payload, user: dict[str, str], module: str, detail_field: str):
    updated = update_entity(db, obj, payload)
    write_log(db, user["username"], user["role"], module, "update", updated.id, str(getattr(updated, detail_field, updated.id)))
    return updated


def delete_with_log(db: Session, obj, user: dict[str, str], module: str, detail_field: str):
    write_log(db, user["username"], user["role"], module, "delete", obj.id, str(getattr(obj, detail_field, obj.id)))
    delete_entity(db, obj)
