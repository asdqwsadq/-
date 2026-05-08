from sqlalchemy.orm import Session

from app.models.entities import OperationLog


def write_log(
    db: Session,
    username: str,
    role: str,
    module: str,
    action: str,
    target_id: int | None = None,
    detail: str | None = None,
):
    log = OperationLog(
        username=username,
        role=role,
        module=module,
        action=action,
        target_id=target_id,
        detail=detail,
    )
    db.add(log)
    db.commit()
