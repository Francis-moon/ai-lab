from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    JSON
)

from .database import Base


class FunctionalZone(Base):
    __tablename__ = "functional_zones"

    id = Column(Integer, primary_key=True)
    zone_id = Column(String, unique=True, index=True)

    site_id = Column(String, default="default_site")
    name = Column(String)
    zone_type = Column(String, index=True)
    # entrance / lane / fire_lane / elevator_lobby / equipment_room / parking_area / loading_area

    floor = Column(String, nullable=True)
    parent_zone_id = Column(String, nullable=True)

    state = Column(String, default="normal")
    heat = Column(Integer, default=1)
    risk_score = Column(Float, default=0.0)

    capacity = Column(Integer, default=0)
    occupancy = Column(Integer, default=0)

    boundary_polygon = Column(JSON, default=list)
    policy = Column(JSON, default=dict)
    attrs = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ZoneTopologyEdge(Base):
    __tablename__ = "zone_topology_edges"

    id = Column(Integer, primary_key=True)

    edge_id = Column(String, unique=True, index=True)
    source_zone_id = Column(String, index=True)
    target_zone_id = Column(String, index=True)

    relation_type = Column(String)
    # adjacent_to / flow_to / blocks / upstream_of / downstream_of

    distance = Column(Float, default=1.0)
    bidirectional = Column(Boolean, default=True)

    state = Column(String, default="normal")
    confidence = Column(Integer, default=100)

    attrs = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)


class SceneNode(Base):
    __tablename__ = "scene_nodes"

    id = Column(Integer, primary_key=True)
    node_id = Column(String, unique=True, index=True)

    node_type = Column(String, index=True)
    name = Column(String)

    zone_id = Column(String, nullable=True)
    floor = Column(String, nullable=True)

    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)
    z = Column(Float, nullable=True)

    state = Column(String, nullable=True)
    confidence = Column(Integer, default=100)

    attrs = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ZoneMember(Base):
    __tablename__ = "zone_members"

    id = Column(Integer, primary_key=True)

    zone_id = Column(String, index=True)
    node_id = Column(String, index=True)

    role = Column(String)
    # anchor / sensor / executor / device / target / passage / evidence

    confidence = Column(Integer, default=100)
    attrs = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)


class SceneEdge(Base):
    __tablename__ = "scene_edges"

    id = Column(Integer, primary_key=True)

    edge_id = Column(String, unique=True, index=True)
    source_node_id = Column(String, index=True)
    target_node_id = Column(String, index=True)

    relation_type = Column(String, index=True)
    relation_state = Column(String, default="confirmed")
    confidence = Column(Integer, default=100)

    evidence_count = Column(Integer, default=0)
    attrs = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)

    event_id = Column(String, unique=True, index=True)
    event_type = Column(String, index=True)

    source = Column(String)
    source_node_id = Column(String, nullable=True)
    target_node_id = Column(String, nullable=True)

    zone_id = Column(String, index=True)
    confidence = Column(Integer, default=60)

    status = Column(String, default="new")
    created_at = Column(DateTime, default=datetime.utcnow)


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True)

    case_id = Column(String, unique=True, index=True)
    case_type = Column(String, index=True)

    zone_id = Column(String, index=True)
    target_node_id = Column(String, nullable=True)

    state = Column(String, default="suspected")
    severity = Column(String, default="medium")
    confidence = Column(Integer, default=50)

    source_event_id = Column(String)
    current_task_id = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)

    task_id = Column(String, unique=True, index=True)
    case_id = Column(String, index=True)

    task_type = Column(String)
    zone_id = Column(String, index=True)
    target_node_id = Column(String, nullable=True)

    priority = Column(String, default="medium")
    sla_minutes = Column(Integer, default=15)

    fallback_chain = Column(String, default="cloud_operator,robot,human")
    assigned_executor_id = Column(String, nullable=True)

    status = Column(String, default="created")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TaskOutcome(Base):
    __tablename__ = "task_outcomes"

    id = Column(Integer, primary_key=True)

    outcome_id = Column(String, unique=True, index=True)
    task_id = Column(String, index=True)
    case_id = Column(String, index=True)

    outcome_type = Column(String)
    confidence = Column(Integer, default=80)

    note = Column(String, nullable=True)
    evidence_url = Column(String, nullable=True)
    created_by = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)


class Executor(Base):
    __tablename__ = "executors"

    id = Column(Integer, primary_key=True)

    executor_id = Column(String, unique=True, index=True)
    executor_type = Column(String)
    # robot / human / cloud_operator / third_party_device

    zone_id = Column(String, index=True)

    status = Column(String, default="idle")
    battery_level = Column(Integer, nullable=True)

    can_handle = Column(String)
    current_task_id = Column(String, nullable=True)

    online = Column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)

    entity_type = Column(String)
    entity_id = Column(String)

    action = Column(String)
    detail = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)