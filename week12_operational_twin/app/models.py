from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from .database import Base


class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True)
    slot_id = Column(String, unique=True, index=True)
    zone = Column(String, index=True)
    state = Column(String, default="free")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True, index=True)
    event_type = Column(String, index=True)
    slot_id = Column(String, nullable=True)
    zone = Column(String, index=True)
    source = Column(String)
    status = Column(String, default="new")
    merged_into = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ZoneState(Base):
    __tablename__ = "zone_states"

    id = Column(Integer, primary_key=True)
    zone = Column(String, unique=True, index=True)
    heat = Column(Integer, default=1)
    status = Column(String, default="normal")
    active_event_count = Column(Integer, default=0)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    task_id = Column(String, unique=True, index=True)
    task_type = Column(String)
    slot_id = Column(String, nullable=True)
    zone = Column(String)
    priority = Column(String, default="medium")
    sla_minutes = Column(Integer, default=30)
    zone_heat = Column(Integer, default=1)

    fallback_chain = Column(String, default="robot,human,cloud_operator")
    assigned_executor_id = Column(String, nullable=True)
    status = Column(String, default="created")

    chain_id = Column(String, nullable=True)
    step_order = Column(Integer, default=1)
    depends_on_task_id = Column(String, nullable=True)


class Executor(Base):
    __tablename__ = "executors"

    id = Column(Integer, primary_key=True)
    executor_id = Column(String, unique=True, index=True)
    executor_type = Column(String)  # robot / human / cloud_operator
    zone = Column(String)
    status = Column(String, default="idle")
    battery_level = Column(Integer, nullable=True)
    current_task_id = Column(String, nullable=True)
    can_handle = Column(String)
    online = Column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String)  # event / task / zone / executor
    entity_id = Column(String)
    action = Column(String)
    detail = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)