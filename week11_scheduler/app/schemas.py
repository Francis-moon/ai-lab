from pydantic import BaseModel
from typing import Optional


class SlotCreate(BaseModel):
    slot_id: str
    zone: str
    state: str = "free"


class SlotUpdateState(BaseModel):
    state: str


class SlotResponse(BaseModel):
    id: int
    slot_id: str
    zone: str
    state: str

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
    preferred_assignee: str = "robot"
    priority: str = "medium"
    sla_minutes: int = 30
    zone_heat: int = 1
    fallback_chain: str = "robot,human,cloud_operator"


class TaskResponse(TaskCreate):
    id: int
    assigned_executor_id: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class ExecutorResponse(BaseModel):
    id: int
    executor_id: str
    executor_type: str
    zone: str
    status: str
    battery_level: Optional[int] = None
    current_task_id: Optional[str] = None
    can_handle: str
    online: bool

    class Config:
        from_attributes = True


class ZoneStateResponse(BaseModel):
    id: int
    zone: str
    heat: int
    status: str

    class Config:
        from_attributes = True