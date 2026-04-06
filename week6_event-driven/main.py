from datetime import datetime
from models import Event, EventType, Slot
from parking_system import ParkingSystem


def seed_system(system: ParkingSystem):
    system.add_slot(Slot(slot_id="Slot-A01", zone_id="Zone-A"))
    system.add_slot(Slot(slot_id="Slot-A02", zone_id="Zone-A"))
    system.add_slot(Slot(slot_id="Slot-B01", zone_id="Zone-B"))


def main():
    system = ParkingSystem()
    seed_system(system)

    system.show_slots()

    # 模拟事件1：B01违停，先进入队列，方便对比普通区域与高优先级区域的排序效果
    event1 = Event(
        event_type=EventType.ILLEGAL_PARKING,
        target_id="Slot-B01",
        timestamp=datetime.now().isoformat(timespec="seconds"),
        payload={"plate_number": "川B88888"}
    )
    system.emit_event(event1)

    # 模拟事件2：A01违停
    event2 = Event(
        event_type=EventType.ILLEGAL_PARKING,
        target_id="Slot-A01",
        timestamp=datetime.now().isoformat(timespec="seconds"),
        payload={"plate_number": "川A12345"}
    )
    system.emit_event(event2)

    # 模拟事件3：A02车位脏污
    event3 = Event(
        event_type=EventType.DIRTY_SLOT,
        target_id="Slot-A02",
        timestamp=datetime.now().isoformat(timespec="seconds"),
        payload={"remark": "oil_stain"}
    )
    system.emit_event(event3)

    # 模拟事件4：A01再次违停，用来验证幂等保护
    event4 = Event(
        event_type=EventType.ILLEGAL_PARKING,
        target_id="Slot-A01",
        timestamp=datetime.now().isoformat(timespec="seconds"),
        payload={"plate_number": "川A23456"}
    )
    system.emit_event(event4)

    # 自动执行直到事件队列和任务队列都清空
    system.run_until_idle()

    system.show_slots()
    system.show_task_history()
    system.show_slot_history("Slot-A01")
    system.show_slot_history("Slot-A02")
    system.show_slot_history("Slot-B01")



if __name__ == "__main__":
    main()