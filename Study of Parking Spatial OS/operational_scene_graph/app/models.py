# 这是一个"可视化、可追踪、高度可扩展"的运营系统框架。 不只管理工单流程，还建立了整个停车场的"知识图谱"
# 包括停车位、车辆、事件、案件等实体，以及它们之间的关系。 通过这个系统，运营人员可以实时了解停车场的状态，快速响应各种事件，并且有完整的审计日志和数据支持决策。
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean
from .database import Base


class SceneNode(Base):
    __tablename__ = "scene_nodes"

    id = Column(Integer, primary_key=True)
    node_id = Column(String, unique=True, index=True)
    node_type = Column(String, index=True)

    name = Column(String)
    zone = Column(String, nullable=True)
    floor = Column(String, nullable=True)

    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)
    z = Column(Float, nullable=True)

    state = Column(String, nullable=True)       # free、occupied、cleaning 等
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

    relation_type = Column(String, index=True)      # adjacent、belongs_to、near、has_robot 等
    confidence = Column(Integer, default=100)

    attrs = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)

    event_id = Column(String, unique=True, index=True)
    event_type = Column(String, index=True)     

    source = Column(String)     # ai_box、cloud_operator、robot 等
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

    state = Column(String, default="suspected")     # suspected → active → closed（案件生命周期）
    severity = Column(String, default="medium")
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

    outcome_type = Column(String)       # confirmed、dismissed、escalated、evidence_captured
    confidence = Column(Integer, default=80)

    evidence_node_id = Column(String, nullable=True)
    note = Column(String, nullable=True)
    created_by = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)


class Executor(Base):
    __tablename__ = "executors"

    id = Column(Integer, primary_key=True)

    executor_id = Column(String, unique=True, index=True)
    executor_type = Column(String)  # robot / human / cloud_operator

    zone = Column(String)
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