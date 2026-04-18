from sqlalchemy import Column, Integer, String
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
    status = Column(String, nullable=False, default="new")  # new / processed / failed


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    task_type = Column(String, nullable=False)
    slot_id = Column(String, nullable=True)
    zone = Column(String, nullable=False)
    assignee = Column(String, nullable=False)  # robot / human / cloud_operator
    priority = Column(String, nullable=False, default="medium")
    status = Column(String, nullable=False, default="created")  # created / in_progress / done