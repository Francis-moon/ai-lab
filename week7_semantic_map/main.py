from datetime import datetime

from models import (
    Zone,
    Lane,
    LaneDirection,
    Slot,
    SlotType,
    Event,
    EventType,
    TargetType,
)
from semantic_map import SemanticMap
from parking_system import ParkingSystem


def seed_map(semantic_map: SemanticMap):
    # 1. Zone
    semantic_map.add_zone(Zone(zone_id="Zone-A", name="A区"))
    semantic_map.add_zone(Zone(zone_id="Zone-B", name="B区"))

    # 2. Lane
    semantic_map.add_lane(
        Lane(
            lane_id="Lane-A1",
            zone_id="Zone-A",
            name="A区主通道",
            direction=LaneDirection.FORWARD,
        )
    )
    semantic_map.add_lane(
        Lane(
            lane_id="Lane-A2",
            zone_id="Zone-A",
            name="A区辅通道",
            direction=LaneDirection.REVERSE,
        )
    )
    semantic_map.add_lane(
        Lane(
            lane_id="Lane-B1",
            zone_id="Zone-B",
            name="B区主通道",
            direction=LaneDirection.BIDIRECTIONAL,
        )
    )

    # 3. Slot
    semantic_map.add_slot(Slot(slot_id="Slot-A01", lane_id="Lane-A1", zone_id="Zone-A", slot_type=SlotType.NORMAL))
    semantic_map.add_slot(Slot(slot_id="Slot-A02", lane_id="Lane-A1", zone_id="Zone-A", slot_type=SlotType.VIP))
    semantic_map.add_slot(Slot(slot_id="Slot-A03", lane_id="Lane-A2", zone_id="Zone-A", slot_type=SlotType.CHARGING))
    semantic_map.add_slot(Slot(slot_id="Slot-B01", lane_id="Lane-B1", zone_id="Zone-B", slot_type=SlotType.CHARGING))
    semantic_map.add_slot(Slot(slot_id="Slot-B02", lane_id="Lane-B1", zone_id="Zone-B", slot_type=SlotType.NORMAL))


def main():
    semantic_map = SemanticMap()
    seed_map(semantic_map)

    system = ParkingSystem(semantic_map)

    # 先打印地图
    semantic_map.show_map_summary()

    # 查询A区空闲车位
    free_slots_a = semantic_map.get_free_slots_by_zone("Zone-A")
    print("\n=== A区空闲车位 ===")
    for slot in free_slots_a:
        print(slot.slot_id)

    # 查询A区空闲充电车位
    free_charging_slots_a = semantic_map.get_free_charging_slots_by_zone("Zone-A")
    print("\n=== A区空闲充电车位 ===")
    for slot in free_charging_slots_a:
        print(slot.slot_id)

    # 事件1：A01违停
    event1 = Event(
        event_type=EventType.ILLEGAL_PARKING,
        target_type=TargetType.SLOT,
        target_id="Slot-A01",
        timestamp=datetime.now().isoformat(),
        payload={"plate_number": "川A12345"},
    )
    system.emit_event(event1)

    # 事件2：A区主通道堵塞
    event2 = Event(
        event_type=EventType.LANE_BLOCKED,
        target_type=TargetType.LANE,
        target_id="Lane-A1",
        timestamp=datetime.now().isoformat(),
        payload={"reason": "临时堆物"},
    )
    system.emit_event(event2)

    # 事件3：Zone-A 被锁定（区域级事件，下钻为该区所有Lane巡检）
    event3 = Event(
        event_type=EventType.ZONE_BLOCKED,
        target_type=TargetType.ZONE,
        target_id="Zone-A",
        timestamp=datetime.now().isoformat(),
        payload={"reason": "区域封控"},
    )
    system.emit_event(event3)

    # 跑完整闭环
    system.process_events()
    system.process_tasks()
    system.process_events()
    system.process_tasks()
    system.process_events()

    # 打印结果
    semantic_map.show_map_summary()
    system.show_task_history()
    system.show_object_context("Slot-A01")
    system.show_slot_history("Slot-A01")

    # 再查一次A区空闲车位
    free_slots_a_after = semantic_map.get_free_slots_by_zone("Zone-A")
    print("\n=== A区当前空闲车位 ===")
    for slot in free_slots_a_after:
        print(slot.slot_id)

    # 最后做一次交互式对象关系问答
    semantic_map.ask_slot_relation_interactive()


if __name__ == "__main__":
    main()