from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .models import SceneEdge, RelationEvidence, SceneNode
from .constants import (
    REL_HYPOTHESIS,
    REL_CONFIRMED,
    REL_REJECTED,
    REL_WEAKENED,
    REL_EXPIRED,
)
from .audit import write_audit


def make_edge_id(source_node_id: str, relation_type: str, target_node_id: str):
    return f"{source_node_id}--{relation_type}--{target_node_id}"


def clamp_confidence(value: int):
    return max(0, min(99, value))


def record_relation_evidence(
    db: Session,
    edge: SceneEdge,
    source_type: str,
    source_id: str,
    action: str,
    confidence_delta: int,
    detail: str,
    created_by: str,
):
    evidence = RelationEvidence(
        evidence_id=f"rel-ev-{edge.edge_id}-{int(datetime.utcnow().timestamp() * 1000)}",
        edge_id=edge.edge_id,
        source_type=source_type,
        source_id=source_id,
        action=action,
        confidence_delta=confidence_delta,
        detail=detail,
        created_by=created_by,
    )

    db.add(evidence)
    db.commit()

    return evidence


def upsert_relation_hypothesis(
    db: Session,
    source_node_id: str,
    relation_type: str,
    target_node_id: str,
    confidence: int,
    created_by: str,
    source_type: str,
    source_id: str,
    detail: str = "",
):
    edge_id = make_edge_id(source_node_id, relation_type, target_node_id)

    edge = db.query(SceneEdge).filter(SceneEdge.edge_id == edge_id).first()

    if not edge:
        edge = SceneEdge(
            edge_id=edge_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation_type=relation_type,
            relation_state=REL_HYPOTHESIS,
            confidence=confidence,
            evidence_count=1,
            created_by=created_by,
            last_observed_at=datetime.utcnow(),
            attrs={},
        )
        db.add(edge)
        db.commit()
        db.refresh(edge)

        record_relation_evidence(
            db,
            edge,
            source_type,
            source_id,
            action="create_hypothesis",
            confidence_delta=confidence,
            detail=detail,
            created_by=created_by,
        )

        write_audit(
            db,
            "scene_edge",
            edge.edge_id,
            "relation_hypothesis_created",
            f"{source_node_id} -[{relation_type}]-> {target_node_id}, conf={confidence}",
        )

        return edge

    edge.confidence = clamp_confidence(max(edge.confidence, confidence))
    edge.evidence_count += 1
    edge.last_observed_at = datetime.utcnow()
    edge.updated_at = datetime.utcnow()

    if edge.relation_state in [REL_REJECTED, REL_EXPIRED]:
        edge.relation_state = REL_HYPOTHESIS

    db.commit()
    db.refresh(edge)

    record_relation_evidence(
        db,
        edge,
        source_type,
        source_id,
        action="strengthen_hypothesis",
        confidence_delta=confidence,
        detail=detail,
        created_by=created_by,
    )

    write_audit(
        db,
        "scene_edge",
        edge.edge_id,
        "relation_hypothesis_strengthened",
        f"conf={edge.confidence}, evidence_count={edge.evidence_count}",
    )

    return edge


def strengthen_relation(
    db: Session,
    source_node_id: str,
    relation_type: str,
    target_node_id: str,
    delta: int,
    source_type: str,
    source_id: str,
    created_by: str,
    detail: str = "",
):
    edge = upsert_relation_hypothesis(
        db=db,
        source_node_id=source_node_id,
        relation_type=relation_type,
        target_node_id=target_node_id,
        confidence=50,
        created_by=created_by,
        source_type=source_type,
        source_id=source_id,
        detail=detail,
    )

    edge.confidence = clamp_confidence(edge.confidence + delta)
    edge.evidence_count += 1
    edge.last_observed_at = datetime.utcnow()
    edge.updated_at = datetime.utcnow()

    if edge.confidence >= 85:
        edge.relation_state = REL_CONFIRMED
        edge.last_verified_at = datetime.utcnow()

    db.commit()
    db.refresh(edge)

    record_relation_evidence(
        db,
        edge,
        source_type,
        source_id,
        action="strengthen",
        confidence_delta=delta,
        detail=detail,
        created_by=created_by,
    )

    return edge


def weaken_relation(
    db: Session,
    source_node_id: str,
    relation_type: str,
    target_node_id: str,
    delta: int,
    source_type: str,
    source_id: str,
    created_by: str,
    detail: str = "",
):
    edge_id = make_edge_id(source_node_id, relation_type, target_node_id)
    edge = db.query(SceneEdge).filter(SceneEdge.edge_id == edge_id).first()

    if not edge:
        return None

    edge.confidence = clamp_confidence(edge.confidence - delta)
    edge.updated_at = datetime.utcnow()

    if edge.confidence <= 20:
        edge.relation_state = REL_REJECTED
    else:
        edge.relation_state = REL_WEAKENED

    db.commit()
    db.refresh(edge)

    record_relation_evidence(
        db,
        edge,
        source_type,
        source_id,
        action="weaken",
        confidence_delta=-delta,
        detail=detail,
        created_by=created_by,
    )

    write_audit(
        db,
        "scene_edge",
        edge.edge_id,
        "relation_weakened",
        f"conf={edge.confidence}, state={edge.relation_state}, reason={detail}",
    )

    return edge


def confirm_relation(
    db: Session,
    source_node_id: str,
    relation_type: str,
    target_node_id: str,
    source_type: str,
    source_id: str,
    created_by: str,
    confidence: int = 95,
    detail: str = "",
):
    edge = upsert_relation_hypothesis(
        db=db,
        source_node_id=source_node_id,
        relation_type=relation_type,
        target_node_id=target_node_id,
        confidence=confidence,
        created_by=created_by,
        source_type=source_type,
        source_id=source_id,
        detail=detail,
    )

    edge.relation_state = REL_CONFIRMED
    edge.confidence = clamp_confidence(confidence)
    edge.last_verified_at = datetime.utcnow()
    edge.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(edge)

    record_relation_evidence(
        db,
        edge,
        source_type,
        source_id,
        action="confirm",
        confidence_delta=confidence,
        detail=detail,
        created_by=created_by,
    )

    write_audit(
        db,
        "scene_edge",
        edge.edge_id,
        "relation_confirmed",
        detail,
    )

    return edge


def reject_relation(
    db: Session,
    source_node_id: str,
    relation_type: str,
    target_node_id: str,
    source_type: str,
    source_id: str,
    created_by: str,
    detail: str = "",
):
    edge_id = make_edge_id(source_node_id, relation_type, target_node_id)
    edge = db.query(SceneEdge).filter(SceneEdge.edge_id == edge_id).first()

    if not edge:
        edge = SceneEdge(
            edge_id=edge_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation_type=relation_type,
            relation_state=REL_REJECTED,
            confidence=0,
            evidence_count=1,
            created_by=created_by,
            attrs={},
        )
        db.add(edge)
    else:
        edge.relation_state = REL_REJECTED
        edge.confidence = 0
        edge.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(edge)

    record_relation_evidence(
        db,
        edge,
        source_type,
        source_id,
        action="reject",
        confidence_delta=-100,
        detail=detail,
        created_by=created_by,
    )

    write_audit(
        db,
        "scene_edge",
        edge.edge_id,
        "relation_rejected",
        detail,
    )

    return edge


def expire_stale_hypotheses(db: Session, hours: int = 24):
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    edges = db.query(SceneEdge).filter(
        SceneEdge.relation_state == REL_HYPOTHESIS,
        SceneEdge.last_observed_at < cutoff,
    ).all()

    results = []

    for edge in edges:
        edge.relation_state = REL_EXPIRED
        edge.updated_at = datetime.utcnow()

        results.append(edge.edge_id)

        write_audit(
            db,
            "scene_edge",
            edge.edge_id,
            "relation_expired",
            f"no observation for {hours} hours",
        )

    db.commit()

    return {
        "expired_count": len(results),
        "edges": results,
    }


def create_or_update_node_state(
    db: Session,
    node_id: str,
    state: str,
    confidence: int,
):
    node = db.query(SceneNode).filter(SceneNode.node_id == node_id).first()

    if not node:
        return None

    node.state = state
    node.confidence = confidence
    node.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(node)

    write_audit(
        db,
        "scene_node",
        node.node_id,
        "node_state_updated",
        f"state={state}, confidence={confidence}",
    )

    return node