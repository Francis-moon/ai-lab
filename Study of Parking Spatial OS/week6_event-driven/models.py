from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class SlotState(str, Enum):
    FREE = "FREE"
    OCCUPIED = "OCCUPIED"
    ILLEGAL = "ILLEGAL"
    BLOCKED = "BLOCKED"
    CHECKING = "CHECKING"
    RESOLVED = "RESOLVED"


class EventType(str, Enum):
    SLOT_OCCUPIED = "SlotOccupied"
    ILLEGAL_PARKING = "IllegalParking"
    LANE_BLOCKED = "LaneBlocked"
    DIRTY_SLOT = "DirtySlot"
    EVIDENCE_CAPTURED = "EvidenceCaptured"
    CLEARED = "Cleared"


class TaskType(str, Enum):
    INSPECT = "Inspect"
    CAPTURE_EVIDENCE = "CaptureEvidence"
    NOTIFY_SECURITY = "NotifySecurity"
    RECHECK = "Recheck"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass
class Event:
    event_type: EventType
    target_id: str
    timestamp: str
    payload: Dict = field(default_factory=dict)


@dataclass
class Task:
    task_id: str
    task_type: TaskType
    target_id: str
    zone_id: str = ""
    priority: int = 1
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass
class Slot:
    slot_id: str
    zone_id: str
    state: SlotState = SlotState.FREE
    history: List[str] = field(default_factory=list)

    def update_state(self, new_state: SlotState):
        old_state = self.state
        self.state = new_state
        log = f"{datetime.now().isoformat(timespec='seconds')} | 状态更新: {self.slot_id} {old_state} -> {new_state}"
        self.history.append(log)
        print(log)
