from datetime import datetime

from sqlalchemy.orm import Session

from .models import (
    FunctionalZone,
    ZoneTopologyEdge,
    ZoneMember,
    SceneNode,
    SceneEdge,
    Task,
    Case,
    Event
)
from .audit import write_audit
from .constants import (
    ZONE_NORMAL,
    ZONE_WARNING,
    ZONE_HIGH_RISK,
    ZONE_BLOCKED
)


def upsert_zone(db: Session, payload):
    zone = db.query(FunctionalZone).filter(
        FunctionalZone.zone_id == payload.zone_id
    ).first()

    if not zone:
        zone = FunctionalZone(
            zone_id=payload.zone_id,
            site_id=payload.site_id,
            name=payload.name,
            zone_type=payload.zone_type,
            floor=payload.floor,
            parent_zone_id=payload.parent_zone_id,
            state=payload.state,
            heat=payload.heat,
            risk_score=payload.risk_score,
            capacity=payload.capacity,
            occupancy=payload.occupancy,
            boundary_polygon=payload.boundary_polygon,
            policy=payload.policy,
            attrs=payload.attrs
        )
        db.add(zone)
        db.commit()
        db.refresh(zone)

        write_audit(
            db,
            "zone",
            zone.zone_id,
            "zone_created",
            f"type={zone.zone_type}, state={zone.state}"
        )

        return zone

    zone.name = payload.name
    zone.zone_type = payload.zone_type
    zone.floor = payload.floor
    zone.parent_zone_id = payload.parent_zone_id
    zone.state = payload.state
    zone.heat = payload.heat
    zone.risk_score = payload.risk_score
    zone.capacity = payload.capacity
    zone.occupancy = payload.occupancy
    zone.boundary_polygon = payload.boundary_polygon
    zone.policy = payload.policy
    zone.attrs = payload.attrs
    zone.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(zone)

    write_audit(
        db,
        "zone",
        zone.zone_id,
        "zone_updated",
        f"state={zone.state}, heat={zone.heat}"
    )

    return zone


def add_zone_topology_edge(db: Session, payload):
    edge = db.query(ZoneTopologyEdge).filter(
        ZoneTopologyEdge.edge_id == payload.edge_id
    ).first()

    if edge:
        return edge

    edge = ZoneTopologyEdge(
        edge_id=payload.edge_id,
        source_zone_id=payload.source_zone_id,
        target_zone_id=payload.target_zone_id,
        relation_type=payload.relation_type,
        distance=payload.distance,
        bidirectional=payload.bidirectional,
        confidence=payload.confidence,
        attrs=payload.attrs
    )

    db.add(edge)
    db.commit()
    db.refresh(edge)

    write_audit(
        db,
        "zone_topology",
        edge.edge_id,
        "zone_topology_created",
        f"{edge.source_zone_id} -[{edge.relation_type}]-> {edge.target_zone_id}"
    )

    return edge


def upsert_scene_node(db: Session, payload):
    node = db.query(SceneNode).filter(
        SceneNode.node_id == payload.node_id
    ).first()

    if not node:
        node = SceneNode(
            node_id=payload.node_id,
            node_type=payload.node_type,
            name=payload.name,
            zone_id=payload.zone_id,
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
            f"type={node.node_type}, zone={node.zone_id}"
        )

        return node

    node.name = payload.name
    node.node_type = payload.node_type
    node.zone_id = payload.zone_id
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

    return node


def link_node_to_zone(db: Session, payload):
    existing = db.query(ZoneMember).filter(
        ZoneMember.zone_id == payload.zone_id,
        ZoneMember.node_id == payload.node_id,
        ZoneMember.role == payload.role
    ).first()

    if existing:
        return existing

    member = ZoneMember(
        zone_id=payload.zone_id,
        node_id=payload.node_id,
        role=payload.role,
        confidence=payload.confidence,
        attrs=payload.attrs
    )

    db.add(member)

    node = db.query(SceneNode).filter(
        SceneNode.node_id == payload.node_id
    ).first()

    if node:
        node.zone_id = payload.zone_id

    db.commit()
    db.refresh(member)

    write_audit(
        db,
        "zone_member",
        f"{payload.zone_id}:{payload.node_id}",
        "zone_member_linked",
        f"role={payload.role}"
    )

    return member


def update_zone_state(db: Session, zone_id: str):
    zone = db.query(FunctionalZone).filter(
        FunctionalZone.zone_id == zone_id
    ).first()

    if not zone:
        raise ValueError("Zone not found")

    open_cases = db.query(Case).filter(
        Case.zone_id == zone_id,
        Case.state != "closed"
    ).count()

    open_tasks = db.query(Task).filter(
        Task.zone_id == zone_id,
        Task.status.in_(["created", "assigned"])
    ).count()

    zone.heat = min(10, 1 + open_cases * 2 + open_tasks)

    if zone.heat <= 2:
        zone.state = ZONE_NORMAL
    elif zone.heat <= 5:
        zone.state = ZONE_WARNING
    elif zone.heat <= 8:
        zone.state = ZONE_HIGH_RISK
    else:
        zone.state = ZONE_BLOCKED

    zone.risk_score = min(100.0, zone.risk_score + open_cases * 0.5)
    zone.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(zone)

    write_audit(
        db,
        "zone",
        zone.zone_id,
        "zone_state_updated",
        f"state={zone.state}, heat={zone.heat}, open_cases={open_cases}, open_tasks={open_tasks}"
    )

    return zone


def get_adjacent_zone_ids(db: Session, zone_id: str):
    edges = db.query(ZoneTopologyEdge).filter(
        (ZoneTopologyEdge.source_zone_id == zone_id) |
        (ZoneTopologyEdge.target_zone_id == zone_id)
    ).all()

    result = set()

    for edge in edges:
        if edge.source_zone_id == zone_id:
            result.add(edge.target_zone_id)

        if edge.bidirectional and edge.target_zone_id == zone_id:
            result.add(edge.source_zone_id)

    return list(result)


def get_zone_context(db: Session, zone_id: str):
    zone = db.query(FunctionalZone).filter(
        FunctionalZone.zone_id == zone_id
    ).first()

    if not zone:
        raise ValueError("Zone not found")

    members = db.query(ZoneMember).filter(
        ZoneMember.zone_id == zone_id
    ).all()

    nodes = []
    for member in members:
        node = db.query(SceneNode).filter(
            SceneNode.node_id == member.node_id
        ).first()
        if node:
            nodes.append(node)

    adjacent_zone_ids = get_adjacent_zone_ids(db, zone_id)

    adjacent_zones = db.query(FunctionalZone).filter(
        FunctionalZone.zone_id.in_(adjacent_zone_ids)
    ).all() if adjacent_zone_ids else []

    open_cases = db.query(Case).filter(
        Case.zone_id == zone_id,
        Case.state != "closed"
    ).all()

    open_tasks = db.query(Task).filter(
        Task.zone_id == zone_id,
        Task.status.in_(["created", "assigned"])
    ).all()

    return {
        "zone": zone,
        "members": members,
        "nodes": nodes,
        "adjacent_zones": adjacent_zones,
        "open_cases": open_cases,
        "open_tasks": open_tasks
    }