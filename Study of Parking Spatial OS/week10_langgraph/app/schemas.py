from pydantic import BaseModel
from typing import Optional


class SlotBase(BaseModel):
    slot_id: str
    zone: str
    state: str


class SlotCreate(BaseModel):
    slot_id: str
    zone: str
    state: str = "free"


class SlotUpdateState(BaseModel):
    state: str


class SlotResponse(SlotBase):
    id: int

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    event_id: str
    event_type: str
    slot_id: Optional[str] = None
    zone: str
    source: str


class EventResponse(EventCreate):
    id: int
    status: str

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    task_id: str
    task_type: str
    slot_id: Optional[str] = None
    zone: str
    assignee: str
    priority: str = "medium"


class TaskResponse(TaskCreate):
    id: int
    status: str

    class Config:
        from_attributes = True