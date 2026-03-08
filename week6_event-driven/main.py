from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime
import uuid


# =========================
# 1. 枚举定义
# =========================
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


# =========================
# 2. 数据模型
# =========================
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


# =========================
# 3. 停车场系统
# =========================
class ParkingSystem:
    def __init__(self):
        self.slots: Dict[str, Slot] = {}
        self.event_queue: List[Event] = []
        self.task_queue: List[Task] = []
        self.task_history: List[Task] = []

    # 初始化车位
    def add_slot(self, slot: Slot):
        self.slots[slot.slot_id] = slot

    # 接收事件
    def emit_event(self, event: Event):
        print(f"\n收到事件: {event.event_type} -> {event.target_id}")
        self.event_queue.append(event)

    # 处理所有事件
    def process_events(self):
        while self.event_queue:
            event = self.event_queue.pop(0)
            self.handle_event(event)

    # 事件处理核心
    def handle_event(self, event: Event):
        slot = self.slots.get(event.target_id)

        if not slot:
            print(f"错误: 未找到目标对象 {event.target_id}")
            return

        # 1) 事件驱动状态更新
        if event.event_type == EventType.SLOT_OCCUPIED:
            slot.update_state(SlotState.OCCUPIED)
            self.create_task(TaskType.RECHECK, slot.slot_id)

        elif event.event_type == EventType.ILLEGAL_PARKING:
            slot.update_state(SlotState.ILLEGAL)
            self.create_task(TaskType.INSPECT, slot.slot_id)
            self.create_task(TaskType.CAPTURE_EVIDENCE, slot.slot_id)
            self.create_task(TaskType.NOTIFY_SECURITY, slot.slot_id)

        elif event.event_type == EventType.LANE_BLOCKED:
            slot.update_state(SlotState.BLOCKED)
            self.create_task(TaskType.INSPECT, slot.slot_id)
            self.create_task(TaskType.NOTIFY_SECURITY, slot.slot_id)

        elif event.event_type == EventType.EVIDENCE_CAPTURED:
            slot.update_state(SlotState.CHECKING)
            self.create_task(TaskType.RECHECK, slot.slot_id)

        elif event.event_type == EventType.CLEARED:
            slot.update_state(SlotState.RESOLVED)

        else:
            print(f"未识别事件类型: {event.event_type}")

    # 创建任务
    def create_task(self, task_type: TaskType, target_id: str):
        task = Task(
            task_id=str(uuid.uuid4())[:8],
            task_type=task_type,
            target_id=target_id
        )
        self.task_queue.append(task)
        print(f"生成任务: {task.task_type} -> {task.target_id}")

    # 执行所有任务
    def process_tasks(self):
        while self.task_queue:
            task = self.task_queue.pop(0)
            self.execute_task(task)

    # 任务执行器
    def execute_task(self, task: Task):
        print(f"开始执行任务: {task.task_type} -> {task.target_id}")

        if task.task_type == TaskType.INSPECT:
            task.result = self.inspect_slot(task.target_id)
            task.status = TaskStatus.DONE

        elif task.task_type == TaskType.CAPTURE_EVIDENCE:
            task.result = self.capture_evidence(task.target_id)
            task.status = TaskStatus.DONE
            # 证据采集后再发一个事件，形成闭环
            new_event = Event(
                event_type=EventType.EVIDENCE_CAPTURED,
                target_id=task.target_id,
                timestamp=datetime.now().isoformat(timespec="seconds"),
                payload={"source_task_id": task.task_id}
            )
            self.emit_event(new_event)

        elif task.task_type == TaskType.NOTIFY_SECURITY:
            task.result = self.notify_security(task.target_id)
            task.status = TaskStatus.DONE

        elif task.task_type == TaskType.RECHECK:
            task.result = self.recheck_slot(task.target_id)
            task.status = TaskStatus.DONE

            # 假设复核后异常已清除，发出 CLEARED
            new_event = Event(
                event_type=EventType.CLEARED,
                target_id=task.target_id,
                timestamp=datetime.now().isoformat(timespec="seconds"),
                payload={"source_task_id": task.task_id}
            )
            self.emit_event(new_event)

        else:
            task.status = TaskStatus.FAILED
            task.result = "未知任务类型"

        self.task_history.append(task)
        print(f"执行完成: {task.task_type}, 结果: {task.result}")

    # =========================
    # 4. 模拟工具函数
    # =========================
    def inspect_slot(self, slot_id: str) -> str:
        return f"{slot_id} 已完成巡检"

    def capture_evidence(self, slot_id: str) -> str:
        return f"{slot_id} 已采集现场证据"

    def notify_security(self, slot_id: str) -> str:
        return f"{slot_id} 已通知安保人员"

    def recheck_slot(self, slot_id: str) -> str:
        return f"{slot_id} 已完成复核，无持续异常"

    # =========================
    # 5. 查看系统状态
    # =========================
    def show_slots(self):
        print("\n=== 当前车位状态 ===")
        for slot in self.slots.values():
            print(f"{slot.slot_id} | zone={slot.zone_id} | state={slot.state}")

    def show_task_history(self):
        print("\n=== 任务执行历史 ===")
        for task in self.task_history:
            print(
                f"{task.task_id} | {task.task_type} | {task.target_id} | "
                f"{task.status} | {task.result}"
            )

    def show_slot_history(self, slot_id: str):
        slot = self.slots.get(slot_id)
        if not slot:
            print(f"未找到车位 {slot_id}")
            return

        print(f"\n=== {slot_id} 状态历史 ===")
        for item in slot.history:
            print(item)


# =========================
# 6. 主程序
# =========================
def seed_system(system: ParkingSystem):
    system.add_slot(Slot(slot_id="Slot-A01", zone_id="Zone-A"))
    system.add_slot(Slot(slot_id="Slot-A02", zone_id="Zone-A"))
    system.add_slot(Slot(slot_id="Slot-B01", zone_id="Zone-B"))


def main():
    system = ParkingSystem()
    seed_system(system)

    system.show_slots()

    # 模拟事件1：A01违停
    event1 = Event(
        event_type=EventType.ILLEGAL_PARKING,
        target_id="Slot-A01",
        timestamp=datetime.now().isoformat(timespec="seconds"),
        payload={"plate_number": "川A12345"}
    )
    system.emit_event(event1)

    # 第1轮：处理事件，生成任务
    system.process_events()

    # 第2轮：执行任务，任务又可能产生新事件
    system.process_tasks()

    # 第3轮：处理任务产生的新事件
    system.process_events()

    # 第4轮：执行新任务
    system.process_tasks()

    # 第5轮：再处理最后一轮事件
    system.process_events()

    system.show_slots()
    system.show_task_history()
    system.show_slot_history("Slot-A01")


if __name__ == "__main__":
    main()