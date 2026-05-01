from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime


class SlotState(str, Enum):
    FREE = "FREE"
    OCCUPIED = "OCCUPIED"
    ILLEGAL = "ILLEGAL"
    BLOCKED = "BLOCKED"
    CHECKING = "CHECKING"
    RESOLVED = "RESOLVED"


class SlotType(str, Enum):
    NORMAL = "NORMAL"
    VIP = "VIP"
    CHARGING = "CHARGING"


class LaneState(str, Enum):
    NORMAL = "NORMAL"
    BLOCKED = "BLOCKED"


class LaneDirection(str, Enum):
    FORWARD = "FORWARD"
    REVERSE = "REVERSE"
    BIDIRECTIONAL = "BIDIRECTIONAL"


class EventType(str, Enum):
    SLOT_OCCUPIED = "SlotOccupied"
    ILLEGAL_PARKING = "IllegalParking"
    LANE_BLOCKED = "LaneBlocked"
    ZONE_BLOCKED = "ZoneBlocked"
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


class TargetType(str, Enum):
    SLOT = "SLOT"
    LANE = "LANE"
    ZONE = "ZONE"


@dataclass
class Event:
    event_type: EventType
    target_type: TargetType
    target_id: str
    timestamp: str
    payload: Dict = field(default_factory=dict)


@dataclass
class Task:
    task_id: str
    task_type: TaskType
    target_type: TargetType
    target_id: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Zone:
    zone_id: str
    name: str
    lane_ids: List[str] = field(default_factory=list)
    history: List[str] = field(default_factory=list)


@dataclass
class Lane:
    lane_id: str
    zone_id: str
    name: str
    direction: LaneDirection = LaneDirection.BIDIRECTIONAL
    state: LaneState = LaneState.NORMAL
    slot_ids: List[str] = field(default_factory=list)
    history: List[str] = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.direction, str):
            try:
                self.direction = LaneDirection(self.direction)
            except ValueError as e:
                raise ValueError(
                    f"非法Lane方向: {self.direction}, 可选值: "
                    f"{[d.value for d in LaneDirection]}"
                ) from e

    def update_state(self, new_state: LaneState):
        old_state = self.state
        self.state = new_state
        log = f"{datetime.now().isoformat()} | Lane状态更新: {self.lane_id} {old_state} -> {new_state}"
        self.history.append(log)
        print(log)


@dataclass
class Slot:
    slot_id: str
    lane_id: str
    zone_id: str
    slot_type: SlotType = SlotType.NORMAL
    state: SlotState = SlotState.FREE
    history: List[str] = field(default_factory=list)

    def update_state(self, new_state: SlotState):
        old_state = self.state
        self.state = new_state
        log = f"{datetime.now().isoformat()} | Slot状态更新: {self.slot_id} {old_state} -> {new_state}"
        self.history.append(log)
        print(log)