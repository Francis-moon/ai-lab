from datetime import datetime
from sqlalchemy.orm import Session

from .models import SceneNode, SceneEdge
from .audit import write_audit


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
            f"type={node.node_type}, name={node.name}"
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


def add_edge(db: Session, payload):
    existing = db.query(SceneEdge).filter(
        SceneEdge.edge_id == payload.edge_id
    ).first()

    if existing:
        return existing

    edge = SceneEdge(
        edge_id=payload.edge_id,
        source_node_id=payload.source_node_id,
        target_node_id=payload.target_node_id,
        relation_type=payload.relation_type,
        confidence=payload.confidence,
        attrs=payload.attrs
    )

    db.add(edge)
    db.commit()
    db.refresh(edge)

    write_audit(
        db,
        "scene_edge",
        edge.edge_id,
        "edge_created",
        f"{edge.source_node_id} -[{edge.relation_type}]-> {edge.target_node_id}"
    )

    return edge


def update_node_state(
    db: Session,
    node_id: str,
    state: str,
    confidence: int = 100
):
    node = db.query(SceneNode).filter(SceneNode.node_id == node_id).first()
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


def get_neighborhood(db: Session, node_id: str):
    outgoing = db.query(SceneEdge).filter(
        SceneEdge.source_node_id == node_id
    ).all()

    incoming = db.query(SceneEdge).filter(
        SceneEdge.target_node_id == node_id
    ).all()

    neighbor_ids = set()

    for e in outgoing:
        neighbor_ids.add(e.target_node_id)

    for e in incoming:
        neighbor_ids.add(e.source_node_id)

    neighbors = db.query(SceneNode).filter(
        SceneNode.node_id.in_(neighbor_ids)
    ).all()

    return {
        "node_id": node_id,
        "outgoing_edges": outgoing,
        "incoming_edges": incoming,
        "neighbors": neighbors
    }


def link_event_to_graph(
    db: Session,
    event_node_id: str,
    target_node_id: str,
    source_node_id: str | None = None
):
    if target_node_id:
        edge_payload = type("EdgePayload", (), {
            "edge_id": f"{event_node_id}-observed-on-{target_node_id}",
            "source_node_id": event_node_id,
            "target_node_id": target_node_id,
            "relation_type": "observed_on",
            "confidence": 90,
            "attrs": {}
        })
        add_edge(db, edge_payload)

    if source_node_id:
        edge_payload = type("EdgePayload", (), {
            "edge_id": f"{source_node_id}-detected-{event_node_id}",
            "source_node_id": source_node_id,
            "target_node_id": event_node_id,
            "relation_type": "detected",
            "confidence": 90,
            "attrs": {}
        })
        add_edge(db, edge_payload)