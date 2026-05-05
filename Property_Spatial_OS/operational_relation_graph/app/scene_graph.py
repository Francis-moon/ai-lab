from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .models import SceneNode, SceneEdge, RelationEvidence, Case, Task, Executor
from .audit import write_audit
from .constants import (
    EDGE_HYPOTHESIS,
    EDGE_CONFIRMED,
    EDGE_REJECTED,
    REL_OBSERVES,
    REL_DETECTED,
    REL_OCCURS_AT,
    REL_ASSIGNED_TO
)


def make_edge_id(
    source_node_id: str,
    relation_type: str,
    target_node_id: str
) -> str:
    raw = f"{source_node_id}|{relation_type}|{target_node_id}"
    return "edge:" + raw.replace(" ", "_")


def upsert_node(db: Session, payload):
    node = db.query(SceneNode).filter(
        SceneNode.node_id == payload.node_id
    ).first()

    if not node:
        node = SceneNode(
            node_id=payload.node_id,
            node_type=payload.node_type,
            name=payload.name,
            zone=payload.zone,
            floor=payload.floor,
            x=payload.x,
            y=payload.y,
            z=payload.z,
            state=payload.state,
            confidence=payload.confidence,
            attrs=payload.attrs
        )

        db.add(node)
        db.commit()
        db.refresh(node)

        write_audit(
            db,
            "scene_node",
            node.node_id,
            "node_created",
            f"type={node.node_type}, state={node.state}"
        )

        return node

    node.name = payload.name
    node.zone = payload.zone
    node.floor = payload.floor
    node.x = payload.x
    node.y = payload.y
    node.z = payload.z
    node.state = payload.state
    node.confidence = payload.confidence
    node.attrs = payload.attrs
    node.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(node)

    write_audit(
        db,
        "scene_node",
        node.node_id,
        "node_updated",
        f"state={node.state}, confidence={node.confidence}"
    )

    return node


def update_node_state(
    db: Session,
    node_id: str,
    state: str,
    confidence: int = 100
):
    node = db.query(SceneNode).filter(
        SceneNode.node_id == node_id
    ).first()

    if not node:
        raise ValueError("Scene node not found")

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
        f"state={state}, confidence={confidence}"
    )

    return node


def record_relation_evidence(
    db: Session,
    edge_id: str,
    signal_type: str,
    source_type: str,
    confidence_delta: int = 0,
    evidence_id: Optional[str] = None,
    source_id: Optional[str] = None,
    event_id: Optional[str] = None,
    task_id: Optional[str] = None,
    case_id: Optional[str] = None,
    note: Optional[str] = None
):
    if not evidence_id:
        evidence_id = f"rel-ev-{edge_id}-{int(datetime.utcnow().timestamp())}"

    evidence = RelationEvidence(
        evidence_id=evidence_id,
        edge_id=edge_id,
        signal_type=signal_type,
        source_type=source_type,
        source_id=source_id,
        event_id=event_id,
        task_id=task_id,
        case_id=case_id,
        confidence_delta=confidence_delta,
        note=note
    )

    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    return evidence


def upsert_relation(
    db: Session,
    source_node_id: str,
    target_node_id: str,
    relation_type: str,
    relation_state: str = EDGE_HYPOTHESIS,
    confidence: int = 60,
    created_by: str = "system",
    source_event_id: Optional[str] = None,
    attrs: Optional[dict] = None,
    evidence_signal: str = "neutral",
    confidence_delta: int = 0,
    evidence_note: Optional[str] = None,
    task_id: Optional[str] = None,
    case_id: Optional[str] = None
):
    if attrs is None:
        attrs = {}

    edge_id = make_edge_id(
        source_node_id=source_node_id,
        relation_type=relation_type,
        target_node_id=target_node_id
    )

    edge = db.query(SceneEdge).filter(
        SceneEdge.edge_id == edge_id
    ).first()

    now = datetime.utcnow()

    if not edge:
        edge = SceneEdge(
            edge_id=edge_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation_type=relation_type,
            relation_state=relation_state,
            confidence=max(0, min(100, confidence)),
            evidence_count=0,
            positive_count=0,
            negative_count=0,
            created_by=created_by,
            source_event_id=source_event_id,
            last_observed_at=now,
            last_verified_at=now if relation_state == EDGE_CONFIRMED else None,
            attrs=attrs
        )

        db.add(edge)
        db.commit()
        db.refresh(edge)

        write_audit(
            db,
            "scene_edge",
            edge.edge_id,
            "edge_created",
            f"{source_node_id} -[{relation_type}/{relation_state}]-> {target_node_id}"
        )

    else:
        edge.confidence = max(0, min(100, edge.confidence + confidence_delta))

        if relation_state == EDGE_CONFIRMED:
            edge.relation_state = EDGE_CONFIRMED
            edge.last_verified_at = now

        elif relation_state == EDGE_REJECTED:
            edge.relation_state = EDGE_REJECTED

        elif relation_state == EDGE_HYPOTHESIS and edge.relation_state != EDGE_CONFIRMED:
            edge.relation_state = EDGE_HYPOTHESIS

        edge.last_observed_at = now
        edge.updated_at = now

        merged_attrs = edge.attrs or {}
        merged_attrs.update(attrs)
        edge.attrs = merged_attrs

        db.commit()
        db.refresh(edge)

        write_audit(
            db,
            "scene_edge",
            edge.edge_id,
            "edge_updated",
            f"state={edge.relation_state}, confidence={edge.confidence}"
        )

    if evidence_signal in ["positive", "negative", "neutral"]:
        edge.evidence_count += 1

        if evidence_signal == "positive":
            edge.positive_count += 1

        elif evidence_signal == "negative":
            edge.negative_count += 1

        db.commit()

        record_relation_evidence(
            db=db,
            edge_id=edge.edge_id,
            signal_type=evidence_signal,
            source_type=created_by,
            confidence_delta=confidence_delta,
            source_id=created_by,
            event_id=source_event_id,
            task_id=task_id,
            case_id=case_id,
            note=evidence_note
        )

    db.refresh(edge)
    return edge


def strengthen_relation(
    db: Session,
    source_node_id: str,
    target_node_id: str,
    relation_type: str,
    amount: int = 10,
    created_by: str = "system",
    source_event_id: Optional[str] = None,
    task_id: Optional[str] = None,
    case_id: Optional[str] = None,
    note: Optional[str] = None
):
    return upsert_relation(
        db=db,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relation_type=relation_type,
        relation_state=EDGE_HYPOTHESIS,
        confidence=60,
        created_by=created_by,
        source_event_id=source_event_id,
        evidence_signal="positive",
        confidence_delta=amount,
        evidence_note=note,
        task_id=task_id,
        case_id=case_id
    )


def weaken_relation(
    db: Session,
    source_node_id: str,
    target_node_id: str,
    relation_type: str,
    amount: int = 15,
    created_by: str = "system",
    source_event_id: Optional[str] = None,
    task_id: Optional[str] = None,
    case_id: Optional[str] = None,
    note: Optional[str] = None
):
    return upsert_relation(
        db=db,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relation_type=relation_type,
        relation_state=EDGE_HYPOTHESIS,
        confidence=60,
        created_by=created_by,
        source_event_id=source_event_id,
        evidence_signal="negative",
        confidence_delta=-amount,
        evidence_note=note,
        task_id=task_id,
        case_id=case_id
    )


def confirm_relation(
    db: Session,
    source_node_id: str,
    target_node_id: str,
    relation_type: str,
    confidence: int = 95,
    created_by: str = "system",
    source_event_id: Optional[str] = None,
    task_id: Optional[str] = None,
    case_id: Optional[str] = None,
    note: Optional[str] = None
):
    return upsert_relation(
        db=db,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relation_type=relation_type,
        relation_state=EDGE_CONFIRMED,
        confidence=confidence,
        created_by=created_by,
        source_event_id=source_event_id,
        evidence_signal="positive",
        confidence_delta=max(0, confidence - 60),
        evidence_note=note,
        task_id=task_id,
        case_id=case_id
    )


def reject_relation(
    db: Session,
    source_node_id: str,
    target_node_id: str,
    relation_type: str,
    created_by: str = "system",
    source_event_id: Optional[str] = None,
    task_id: Optional[str] = None,
    case_id: Optional[str] = None,
    note: Optional[str] = None
):
    return upsert_relation(
        db=db,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relation_type=relation_type,
        relation_state=EDGE_REJECTED,
        confidence=0,
        created_by=created_by,
        source_event_id=source_event_id,
        evidence_signal="negative",
        confidence_delta=-100,
        evidence_note=note,
        task_id=task_id,
        case_id=case_id
    )


def get_neighborhood(db: Session, node_id: str):
    outgoing = db.query(SceneEdge).filter(
        SceneEdge.source_node_id == node_id
    ).all()

    incoming = db.query(SceneEdge).filter(
        SceneEdge.target_node_id == node_id
    ).all()

    neighbor_ids = set()

    for edge in outgoing:
        neighbor_ids.add(edge.target_node_id)

    for edge in incoming:
        neighbor_ids.add(edge.source_node_id)

    nodes = db.query(SceneNode).filter(
        SceneNode.node_id.in_(neighbor_ids)
    ).all() if neighbor_ids else []

    return {
        "node_id": node_id,
        "neighbors": nodes,
        "incoming_edges": incoming,
        "outgoing_edges": outgoing
    }


def get_case_relevant_subgraph(db: Session, case_id: str):
    case = db.query(Case).filter(
        Case.case_id == case_id
    ).first()

    if not case:
        raise ValueError("Case not found")

    node_ids = set()

    case_node_id = f"case:{case.case_id}"
    event_node_id = f"event:{case.source_event_id}"

    node_ids.add(case_node_id)
    node_ids.add(event_node_id)

    if case.target_node_id:
        node_ids.add(case.target_node_id)

    tasks = db.query(Task).filter(
        Task.case_id == case.case_id
    ).all()

    for task in tasks:
        node_ids.add(f"task:{task.task_id}")

    if case.current_task_id:
        current_task = db.query(Task).filter(
            Task.task_id == case.current_task_id
        ).first()

        if current_task:
            executors = db.query(Executor).filter(
                Executor.zone == current_task.zone,
                Executor.online == True
            ).all()

            for executor in executors:
                node_ids.add(f"executor:{executor.executor_id}")

    expanded = set(node_ids)

    for node_id in list(node_ids):
        edges = db.query(SceneEdge).filter(
            (SceneEdge.source_node_id == node_id) |
            (SceneEdge.target_node_id == node_id)
        ).all()

        for edge in edges:
            expanded.add(edge.source_node_id)
            expanded.add(edge.target_node_id)

    nodes = db.query(SceneNode).filter(
        SceneNode.node_id.in_(expanded)
    ).all()

    edges = db.query(SceneEdge).filter(
        SceneEdge.source_node_id.in_(expanded),
        SceneEdge.target_node_id.in_(expanded)
    ).all()

    return {
        "case_id": case_id,
        "nodes": nodes,
        "edges": edges
    }