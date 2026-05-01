from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EventCreate(BaseModel):
    event_id: str
    event_type: str
    slot_id: Optional[str] = None
    zone: str
    source: str


class EventResponse(EventCreate):
    id: int
    status: str
    merged_into: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    task_id: str
    task_type: str
    slot_id: Optional[str] = None
    zone: str
    priority: str = "medium"
    sla_minutes: int = 30
    zone_heat: int = 1
    fallback_chain: str = "robot,human,cloud_operator"
    chain_id: Optional[str] = None
    step_order: int = 1
    depends_on_task_id: Optional[str] = None


class TaskResponse(TaskCreate):
    id: int
    assigned_executor_id: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class ZoneResponse(BaseModel):
    id: int
    zone: str
    heat: int
    status: str
    active_event_count: int

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


class AuditResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    action: str
    detail: str
    created_at: datetime

    class Config:
        from_attributes = True