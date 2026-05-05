from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from .database import Base


class SceneNode(Base):
    __tablename__ = "scene_nodes"

    id = Column(Integer, primary_key=True)
    node_id = Column(String, unique=True, index=True)
    node_type = Column(String, index=True)

    name = Column(String)
    zone = Column(String, nullable=True)
    state = Column(String, nullable=True)
    confidence = Column(Integer, default=100)

    attrs = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class SceneEdge(Base):
    __tablename__ = "scene_edges"

    id = Column(Integer, primary_key=True)

    edge_id = Column(String, unique=True, index=True)

    source_node_id = Column(String, index=True)
    target_node_id = Column(String, index=True)

    relation_type = Column(String, index=True)
    # observes / supports / occupies / verifies / controls / reachable_by / produces

    relation_state = Column(String, default="hypothesis")
    # hypothesis / confirmed / rejected / weakened / expired

    confidence = Column(Integer, default=50)
    evidence_count = Column(Integer, default=0)

    created_by = Column(String, default="system")
    # manual_config / ai_box / robot / human / cloud_operator / system

    last_observed_at = Column(DateTime, nullable=True)
    last_verified_at = Column(DateTime, nullable=True)

    attrs = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class RelationEvidence(Base):
    __tablename__ = "relation_evidence"

    id = Column(Integer, primary_key=True)

    evidence_id = Column(String, unique=True, index=True)
    edge_id = Column(String, index=True)

    source_type = Column(String)
    # event / task_outcome / feedback / manual_config / robot_verify

    source_id = Column(String)

    action = Column(String)
    # strengthen / weaken / confirm / reject / expire

    confidence_delta = Column(Integer, default=0)

    detail = Column(String, nullable=True)
    created_by = Column(String, default="system")

    created_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)

    event_id = Column(String, unique=True, index=True)
    event_type = Column(String, index=True)

    source = Column(String)
    source_node_id = Column(String, nullable=True)
    target_node_id = Column(String, nullable=True)

    zone = Column(String)
    confidence = Column(Integer, default=60)
    status = Column(String, default="new")

    created_at = Column(DateTime, default=datetime.utcnow)


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True)

    case_id = Column(String, unique=True, index=True)
    case_type = Column(String, index=True)

    state = Column(String, default="suspected")
    confidence = Column(Integer, default=50)

    zone = Column(String)
    target_node_id = Column(String, nullable=True)

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
    target_node_id = Column(String, nullable=True)
    zone = Column(String)

    priority = Column(String, default="medium")
    sla_minutes = Column(Integer, default=15)

    fallback_chain = Column(String, default="cloud_operator,robot,human")
    assigned_executor_id = Column(String, nullable=True)

    status = Column(String, default="created")

    created_at = Column(DateTime, default=datetime.utcnow)


class TaskOutcome(Base):
    __tablename__ = "task_outcomes"

    id = Column(Integer, primary_key=True)

    outcome_id = Column(String, unique=True, index=True)
    task_id = Column(String, index=True)
    case_id = Column(String, index=True)

    outcome_type = Column(String)
    confidence = Column(Integer, default=80)

    evidence_node_id = Column(String, nullable=True)
    note = Column(String, nullable=True)
    created_by = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)


class Executor(Base):
    __tablename__ = "executors"

    id = Column(Integer, primary_key=True)

    executor_id = Column(String, unique=True, index=True)
    executor_type = Column(String)

    zone = Column(String)
    status = Column(String, default="idle")

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