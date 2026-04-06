from typing import List
from datetime import datetime
import uuid

from models import (
    Event,
    Task,
    TaskType,
    TaskStatus,
    EventType,
    TargetType,
)
from handlers import handle_event_rules
from tools import (
    inspect_slot,
    inspect_lane,
    capture_evidence,
    notify_security,
    recheck_slot,
)
from semantic_map import SemanticMap


class ParkingSystem:
    def __init__(self, semantic_map: SemanticMap):
        self.semantic_map = semantic_map
        self.event_queue: List[Event] = []
        self.task_queue: List[Task] = []
        self.task_history: List[Task] = []

    # ===== 事件 =====
    def emit_event(self, event: Event):
        print(f"\n收到事件: {event.event_type} -> {event.target_type}:{event.target_id}")
        self.event_queue.append(event)

    def process_events(self):
        while self.event_queue:
            event = self.event_queue.pop(0)
            self.handle_event(event)

    def handle_event(self, event: Event):
        handle_event_rules(self, event)

    # ===== 任务 =====
    def create_task(self, task_type: TaskType, target_type: TargetType, target_id: str):
        task = Task(
            task_id=str(uuid.uuid4())[:8],
            task_type=task_type,
            target_type=target_type,
            target_id=target_id,
        )
        self.task_queue.append(task)
        print(f"生成任务: {task.task_type} -> {task.target_type}:{task.target_id}")

    def process_tasks(self):
        while self.task_queue:
            task = self.task_queue.pop(0)
            self.execute_task(task)

    def execute_task(self, task: Task):
        print(f"开始执行任务: {task.task_type} -> {task.target_type}:{task.target_id}")

        if task.task_type == TaskType.INSPECT:
            if task.target_type == TargetType.SLOT:
                task.result = inspect_slot(task.target_id)
                task.status = TaskStatus.DONE
            elif task.target_type == TargetType.LANE:
                task.result = inspect_lane(task.target_id)
                task.status = TaskStatus.DONE
            else:
                task.status = TaskStatus.FAILED
                task.result = "INSPECT暂不支持该目标类型"

        elif task.task_type == TaskType.CAPTURE_EVIDENCE:
            task.result = capture_evidence(task.target_id)
            task.status = TaskStatus.DONE

            new_event = Event(
                event_type=EventType.EVIDENCE_CAPTURED,
                target_type=task.target_type,
                target_id=task.target_id,
                timestamp=datetime.now().isoformat(),
                payload={"source_task_id": task.task_id},
            )
            self.emit_event(new_event)

        elif task.task_type == TaskType.NOTIFY_SECURITY:
            task.result = notify_security(task.target_id)
            task.status = TaskStatus.DONE

        elif task.task_type == TaskType.RECHECK:
            if task.target_type == TargetType.SLOT:
                task.result = recheck_slot(task.target_id)
                task.status = TaskStatus.DONE

                new_event = Event(
                    event_type=EventType.CLEARED,
                    target_type=task.target_type,
                    target_id=task.target_id,
                    timestamp=datetime.now().isoformat(),
                    payload={"source_task_id": task.task_id},
                )
                self.emit_event(new_event)
            else:
                task.status = TaskStatus.FAILED
                task.result = "RECHECK暂不支持该目标类型"

        else:
            task.status = TaskStatus.FAILED
            task.result = "未知任务类型"

        self.task_history.append(task)
        print(f"执行完成: {task.task_type}, 结果: {task.result}")

    # ===== 展示 =====
    def show_task_history(self):
        print("\n=== 任务执行历史 ===")
        for task in self.task_history:
            print(
                f"{task.task_id} | {task.task_type} | "
                f"{task.target_type}:{task.target_id} | "
                f"{task.status} | {task.result}"
            )

    def show_object_context(self, slot_id: str):
        slot = self.semantic_map.get_slot(slot_id)
        if not slot:
            print(f"未找到Slot: {slot_id}")
            return

        lane = self.semantic_map.get_lane_of_slot(slot_id)
        zone = self.semantic_map.get_zone_of_slot(slot_id)

        print("\n=== 对象上下文 ===")
        print(f"Slot: {slot.slot_id}, state={slot.state}")
        print(f"Lane: {lane.lane_id if lane else 'N/A'}, state={lane.state if lane else 'N/A'}")
        print(f"Zone: {zone.zone_id if zone else 'N/A'}, name={zone.name if zone else 'N/A'}")

    def show_slot_history(self, slot_id: str):
        slot = self.semantic_map.get_slot(slot_id)
        if not slot:
            print(f"未找到Slot: {slot_id}")
            return

        print(f"\n=== {slot_id} 状态历史 ===")
        for item in slot.history:
            print(item)