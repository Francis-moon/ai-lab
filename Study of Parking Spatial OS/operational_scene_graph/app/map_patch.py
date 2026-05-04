# 这是“地图逐步校正”的最小实现。
# 生产环境中，地图 patch 应该有人工审批；这里先给教学版。
from datetime import datetime
from sqlalchemy.orm import Session

from .models import MapPatch, SceneNode
from .audit import write_audit


def propose_map_patch(
    db: Session,
    target_node_id: str,
    patch_type: str,
    payload: dict,
    source_case_id: str | None = None,
    proposed_by: str = "system"
):
    patch = MapPatch(
        patch_id=f"patch-{target_node_id}-{int(datetime.utcnow().timestamp())}",
        target_node_id=target_node_id,
        patch_type=patch_type,
        payload=payload,
        source_case_id=source_case_id,
        proposed_by=proposed_by,
        status="proposed"
    )

    db.add(patch)
    db.commit()
    db.refresh(patch)

    write_audit(
        db,
        "map_patch",
        patch.patch_id,
        "map_patch_proposed",
        f"target={target_node_id}, type={patch_type}"
    )

    return patch


def apply_map_patch(db: Session, patch_id: str):
    patch = db.query(MapPatch).filter(
        MapPatch.patch_id == patch_id
    ).first()

    if not patch:
        raise ValueError("Patch not found")

    if patch.status != "proposed":
        raise ValueError("Patch already processed")

    node = db.query(SceneNode).filter(
        SceneNode.node_id == patch.target_node_id
    ).first()

    if not node:
        raise ValueError("Target scene node not found")

    if patch.patch_type == "update_attrs":
        attrs = node.attrs or {}
        attrs.update(patch.payload)
        node.attrs = attrs

    elif patch.patch_type == "mark_blindspot":
        attrs = node.attrs or {}
        attrs["blindspot"] = True
        attrs["blindspot_note"] = patch.payload.get("note")
        node.attrs = attrs

    elif patch.patch_type == "update_node_state":
        node.state = patch.payload.get("state", node.state)

    patch.status = "applied"
    patch.applied_at = datetime.utcnow()

    db.commit()

    write_audit(
        db,
        "map_patch",
        patch.patch_id,
        "map_patch_applied",
        f"target={patch.target_node_id}"
    )

    return {
        "patch_id": patch.patch_id,
        "status": patch.status,
        "target_node_id": patch.target_node_id
    }


def reject_map_patch(db: Session, patch_id: str, reason: str):
    patch = db.query(MapPatch).filter(
        MapPatch.patch_id == patch_id
    ).first()

    if not patch:
        raise ValueError("Patch not found")

    patch.status = "rejected"
    db.commit()

    write_audit(
        db,
        "map_patch",
        patch.patch_id,
        "map_patch_rejected",
        reason
    )

    return {
        "patch_id": patch.patch_id,
        "status": patch.status,
        "reason": reason
    }
