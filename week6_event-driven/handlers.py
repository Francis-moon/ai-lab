"""
放事件处理规则：
 -什么事件触发什么状态变化
 -什么事件生成什么任务
这就是“规则中枢”。
例如：
违停 → 改状态 → 派巡检/取证/通知
取证完成 → 派复核
复核完成 → 清除异常
以后你接入大模型时，大模型也大概率只替代这一层的一部分，不会替代整个系统。
"""

from datetime import datetime
from typing import TYPE_CHECKING

from models import Event, EventType, SlotState, Task, TaskType

if TYPE_CHECKING:
    from parking_system import ParkingSystem


def handle_event(system: "ParkingSystem", event: Event):
    slot = system.slots.get(event.target_id)

    if not slot:
        print(f"错误: 未找到目标对象 {event.target_id}")
        return

    if event.event_type == EventType.SLOT_OCCUPIED:
        slot.update_state(SlotState.OCCUPIED)
        system.create_task(TaskType.RECHECK, slot.slot_id, slot.zone_id)

    elif event.event_type == EventType.ILLEGAL_PARKING:
        if slot.state == SlotState.ILLEGAL:
            print(f"状态保护: {slot.slot_id} 已处于 ILLEGAL，忽略重复 IllegalParking")
            return

        slot.update_state(SlotState.ILLEGAL)
        system.create_task(TaskType.INSPECT, slot.slot_id, slot.zone_id)
        system.create_task(TaskType.CAPTURE_EVIDENCE, slot.slot_id, slot.zone_id)
        system.create_task(TaskType.NOTIFY_SECURITY, slot.slot_id, slot.zone_id)

    elif event.event_type == EventType.LANE_BLOCKED:
        slot.update_state(SlotState.BLOCKED)
        system.create_task(TaskType.INSPECT, slot.slot_id, slot.zone_id)
        system.create_task(TaskType.NOTIFY_SECURITY, slot.slot_id, slot.zone_id)

    elif event.event_type == EventType.DIRTY_SLOT:
        slot.update_state(SlotState.CHECKING)
        system.create_task(TaskType.INSPECT, slot.slot_id, slot.zone_id)

    elif event.event_type == EventType.EVIDENCE_CAPTURED:
        slot.update_state(SlotState.CHECKING)
        system.create_task(TaskType.RECHECK, slot.slot_id, slot.zone_id)

    elif event.event_type == EventType.CLEARED:
        slot.update_state(SlotState.RESOLVED)

    else:
        print(f"未识别事件类型: {event.event_type}")


def handle_task_post_rules(system: "ParkingSystem", task: Task):
    if task.task_type == TaskType.INSPECT:
        slot = system.slots.get(task.target_id)
        if slot and slot.state == SlotState.CHECKING:
            system.create_task(TaskType.RECHECK, task.target_id, slot.zone_id)

    elif task.task_type == TaskType.CAPTURE_EVIDENCE:
        new_event = Event(
            event_type=EventType.EVIDENCE_CAPTURED,
            target_id=task.target_id,
            timestamp=datetime.now().isoformat(timespec="seconds"),
            payload={"source_task_id": task.task_id},
        )
        system.emit_event(new_event)

    elif task.task_type == TaskType.RECHECK:
        new_event = Event(
            event_type=EventType.CLEARED,
            target_id=task.target_id,
            timestamp=datetime.now().isoformat(timespec="seconds"),
            payload={"source_task_id": task.task_id},
        )
        system.emit_event(new_event)
