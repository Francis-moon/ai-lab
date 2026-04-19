from sqlalchemy import Column, Integer, String, Boolean
from .database import Base


class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(String, unique=True, index=True, nullable=False)
    zone = Column(String, index=True, nullable=False)
    state = Column(String, nullable=False, default="free")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False)
    event_type = Column(String, nullable=False)
    slot_id = Column(String, nullable=True)
    zone = Column(String, nullable=False)
    source = Column(String, nullable=False)
    status = Column(String, nullable=False, default="new")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    task_type = Column(String, nullable=False)
    slot_id = Column(String, nullable=True)
    zone = Column(String, nullable=False)

    preferred_assignee = Column(String, nullable=False, default="robot")
    assigned_executor_id = Column(String, nullable=True)

    priority = Column(String, nullable=False, default="medium")
    sla_minutes = Column(Integer, nullable=False, default=30)
    zone_heat = Column(Integer, nullable=False, default=1)

    fallback_chain = Column(String, nullable=False, default="robot,human,cloud_operator")
    status = Column(String, nullable=False, default="created")


class Executor(Base):
    __tablename__ = "executors"

    id = Column(Integer, primary_key=True, index=True)
    executor_id = Column(String, unique=True, index=True, nullable=False)
    executor_type = Column(String, nullable=False)  # robot / human / cloud_operator
    zone = Column(String, nullable=False)

    status = Column(String, nullable=False, default="idle")
    battery_level = Column(Integer, nullable=True)  # only for robot
    current_task_id = Column(String, nullable=True)
    can_handle = Column(String, nullable=False)  # 逗号分隔 task_type
    online = Column(Boolean, nullable=False, default=True)


class ZoneState(Base):
    __tablename__ = "zone_states"

    id = Column(Integer, primary_key=True, index=True)
    zone = Column(String, unique=True, index=True, nullable=False)
    heat = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="normal")  # normal / congested / blocked / high_risk