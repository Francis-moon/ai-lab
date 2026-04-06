"""
放系统主类：
-队列管理
-处理事件
-生成和执行任务
-记录和展示日志
这就是“调度中枢”。
以后这里就会逐步演化成：
-调度器
-工单系统
-多Agent Runtime
"""
import uuid
from typing import Dict, List, Optional

from handlers import handle_event, handle_task_post_rules
from models import Event, Slot, Task, TaskStatus, TaskType
from tools import capture_evidence, inspect_slot, notify_security, recheck_slot


class ParkingSystem:
    TASK_PRIORITIES = {
        TaskType.NOTIFY_SECURITY: 1,
        TaskType.CAPTURE_EVIDENCE: 2,
        TaskType.RECHECK: 3,
        TaskType.INSPECT: 4,
    }
    ZONE_PRIORITY_OFFSETS = {
        "Zone-A": 0,
        "Zone-B": 100,
    }

    def __init__(self):
        self.slots: Dict[str, Slot] = {}
        self.event_queue: List[Event] = []
        self.task_queue: List[Task] = []
        self.task_history: List[Task] = []

    def add_slot(self, slot: Slot):
        self.slots[slot.slot_id] = slot

    def emit_event(self, event: Event):
        print(f"\\n收到事件: {event.event_type} -> {event.target_id}")
        self.event_queue.append(event)

    def process_events(self):
        while self.event_queue:
            event = self.event_queue.pop(0)
            handle_event(self, event)

    def create_task(self, task_type: TaskType, target_id: str, zone_id: Optional[str] = None):
        slot = self.slots.get(target_id)
        effective_zone_id = zone_id or (slot.zone_id if slot else "")
        base_priority = self.TASK_PRIORITIES.get(task_type, 1)
        zone_priority_offset = self.ZONE_PRIORITY_OFFSETS.get(effective_zone_id, 100)

        task = Task(
            task_id=str(uuid.uuid4())[:8],
            task_type=task_type,
            target_id=target_id,
            zone_id=effective_zone_id,
            priority=zone_priority_offset + base_priority,
        )
        self.task_queue.append(task)
        print(f"生成任务: {task.task_type} -> {task.target_id} | zone={task.zone_id} | priority={task.priority}")

    def process_tasks(self):
        self.task_queue.sort(key=lambda task: task.priority)
        while self.task_queue:
            task = self.task_queue.pop(0)
            self.execute_task(task)

    def run_until_idle(self, max_rounds: int = 50):
        rounds = 0
        while (self.event_queue or self.task_queue) and rounds < max_rounds:
            rounds += 1
            print(f"\\n--- 调度轮次 {rounds} ---")
            self.process_events()
            self.process_tasks()

        if self.event_queue or self.task_queue:
            print(f"警告: 达到最大轮次 {max_rounds}，队列仍未清空")
        else:
            print(f"\\n调度完成，共执行 {rounds} 轮")

    def execute_task(self, task: Task):
        print(f"开始执行任务: {task.task_type} -> {task.target_id}")

        if task.task_type == TaskType.INSPECT:
            task.result = inspect_slot(task.target_id)
            task.status = TaskStatus.DONE

        elif task.task_type == TaskType.CAPTURE_EVIDENCE:
            task.result = capture_evidence(task.target_id)
            task.status = TaskStatus.DONE

        elif task.task_type == TaskType.NOTIFY_SECURITY:
            task.result = notify_security(task.target_id)
            task.status = TaskStatus.DONE

        elif task.task_type == TaskType.RECHECK:
            task.result = recheck_slot(task.target_id)
            task.status = TaskStatus.DONE

        else:
            task.status = TaskStatus.FAILED
            task.result = "未知任务类型"

        if task.status == TaskStatus.DONE:
            handle_task_post_rules(self, task)

        self.task_history.append(task)
        print(f"执行完成: {task.task_type}, 结果: {task.result}")

    def show_slots(self):
        print("\\n=== 当前车位状态 ===")
        for slot in self.slots.values():
            print(f"{slot.slot_id} | zone={slot.zone_id} | state={slot.state}")

    def show_task_history(self):
        print("\\n=== 任务执行历史 ===")
        for task in self.task_history:
            print(
                f"{task.task_id} | {task.task_type} | {task.target_id} | {task.zone_id} | "
                f"{task.priority} | {task.status} | {task.result}"
            )

    def show_slot_history(self, slot_id: str):
        slot = self.slots.get(slot_id)
        if not slot:
            print(f"未找到车位 {slot_id}")
            return

        print(f"\\n=== {slot_id} 状态历史 ===")
        for item in slot.history:
            print(item)
