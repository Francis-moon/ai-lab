from sqlalchemy.orm import Session

from .models import AuditLog


def write_audit(
    db: Session,
    entity_type: str,
    entity_id: str,
    action: str,
    detail: str
):
    log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        detail=detail
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log