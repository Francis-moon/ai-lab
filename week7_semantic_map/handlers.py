from models import (
    EventType,
    SlotState,
    LaneState,
    TaskType,
    TargetType,
)


def handle_event_rules(system, event):
    """
    system 提供 semantic_map / create_task
    event 是当前事件
    """
    semantic_map = system.semantic_map

    if event.target_type == TargetType.SLOT:
        slot = semantic_map.get_slot(event.target_id)
        if not slot:
            print(f"未找到Slot: {event.target_id}")
            return

        if event.event_type == EventType.SLOT_OCCUPIED:
            slot.update_state(SlotState.OCCUPIED)
            system.create_task(TaskType.RECHECK, TargetType.SLOT, slot.slot_id)

        elif event.event_type == EventType.ILLEGAL_PARKING:
            slot.update_state(SlotState.ILLEGAL)
            system.create_task(TaskType.INSPECT, TargetType.SLOT, slot.slot_id)
            system.create_task(TaskType.CAPTURE_EVIDENCE, TargetType.SLOT, slot.slot_id)
            system.create_task(TaskType.NOTIFY_SECURITY, TargetType.SLOT, slot.slot_id)

        elif event.event_type == EventType.EVIDENCE_CAPTURED:
            slot.update_state(SlotState.CHECKING)
            system.create_task(TaskType.RECHECK, TargetType.SLOT, slot.slot_id)

        elif event.event_type == EventType.CLEARED:
            slot.update_state(SlotState.RESOLVED)

        else:
            print(f"Slot对象暂不支持事件: {event.event_type}")

    elif event.target_type == TargetType.LANE:
        lane = semantic_map.get_lane(event.target_id)
        if not lane:
            print(f"未找到Lane: {event.target_id}")
            return

        if event.event_type == EventType.LANE_BLOCKED:
            lane.update_state(LaneState.BLOCKED)
            system.create_task(TaskType.INSPECT, TargetType.LANE, lane.lane_id)
            system.create_task(TaskType.NOTIFY_SECURITY, TargetType.LANE, lane.lane_id)

        elif event.event_type == EventType.CLEARED:
            lane.update_state(LaneState.NORMAL)

        else:
            print(f"Lane对象暂不支持事件: {event.event_type}")

    elif event.target_type == TargetType.ZONE:
        zone = semantic_map.get_zone(event.target_id)
        if not zone:
            print(f"未找到Zone: {event.target_id}")
            return

        if event.event_type == EventType.ZONE_BLOCKED:
            lanes = semantic_map.get_lanes_by_zone(zone.zone_id)
            if not lanes:
                print(f"Zone下无Lane可巡检: {zone.zone_id}")
                return

            for lane in lanes:
                system.create_task(TaskType.INSPECT, TargetType.LANE, lane.lane_id)

        else:
            print(f"Zone对象暂不支持事件: {event.event_type}")

    else:
        print(f"暂不支持的target_type: {event.target_type}")