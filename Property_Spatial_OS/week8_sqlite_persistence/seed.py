from sqlalchemy.orm import Session

from crud import bulk_create_100_slots, update_slot_state


def seed_data(db: Session):
    bulk_create_100_slots(db)


def simulate_status_changes(db: Session):
    # 模拟几个典型状态变化
    update_slot_state(
        db,
        slot_id="Slot-A-1-01",
        new_state="OCCUPIED",
        reason="车辆驶入车位",
        event_type="SlotOccupied"
    )

    update_slot_state(
        db,
        slot_id="Slot-A-1-02",
        new_state="ILLEGAL",
        reason="发现违停",
        event_type="IllegalParking"
    )

    update_slot_state(
        db,
        slot_id="Slot-A-1-02",
        new_state="CHECKING",
        reason="已触发复核流程",
        event_type="EvidenceCaptured"
    )

    update_slot_state(
        db,
        slot_id="Slot-A-1-02",
        new_state="RESOLVED",
        reason="复核完成，异常解除",
        event_type="Cleared"
    )

    update_slot_state(
        db,
        slot_id="Slot-B-2-03",
        new_state="BLOCKED",
        reason="通道附近障碍影响车位使用",
        event_type="LaneBlocked"
    )

    update_slot_state(
        db,
        slot_id="Slot-C-1-05",
        new_state="OCCUPIED",
        reason="车辆正常停入",
        event_type="SlotOccupied"
    )