from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from models import Slot, SlotHistory


# =========================
# 1. 创建 Slot
# =========================
def create_slot(
    db: Session,
    slot_id: str,
    zone_id: str,
    lane_id: str,
    slot_type: str = "NORMAL",
    state: str = "FREE"
) -> Slot:
    slot = Slot(
        slot_id=slot_id,
        zone_id=zone_id,
        lane_id=lane_id,
        slot_type=slot_type,
        state=state
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)

    # 初始创建也写入一条历史，方便以后审计
    history = SlotHistory(
        slot_id_fk=slot.id,
        slot_id=slot.slot_id,
        from_state="NONE",
        to_state=slot.state,
        reason="INITIAL_CREATE",
        event_type="INIT"
    )
    db.add(history)
    db.commit()

    return slot


# =========================
# 2. 查询
# =========================
def get_slot_by_slot_id(db: Session, slot_id: str) -> Optional[Slot]:
    return db.query(Slot).filter(Slot.slot_id == slot_id).first()


def get_all_slots(db: Session) -> List[Slot]:
    return db.query(Slot).order_by(Slot.slot_id).all()


def get_slots_by_zone(db: Session, zone_id: str) -> List[Slot]:
    return db.query(Slot).filter(Slot.zone_id == zone_id).order_by(Slot.slot_id).all()


def get_free_slots_by_zone(db: Session, zone_id: str) -> List[Slot]:
    return (
        db.query(Slot)
        .filter(Slot.zone_id == zone_id, Slot.state == "FREE")
        .order_by(Slot.slot_id)
        .all()
    )


def get_slot_histories(db: Session, slot_id: str) -> List[SlotHistory]:
    return (
        db.query(SlotHistory)
        .filter(SlotHistory.slot_id == slot_id)
        .order_by(SlotHistory.created_at.asc())
        .all()
    )


# =========================
# 3. 更新状态
# =========================
def update_slot_state(
    db: Session,
    slot_id: str,
    new_state: str,
    reason: str,
    event_type: Optional[str] = None
) -> Optional[Slot]:
    slot = get_slot_by_slot_id(db, slot_id)
    if not slot:
        print(f"未找到车位: {slot_id}")
        return None

    old_state = slot.state
    if old_state == new_state:
        print(f"{slot_id} 状态未变化，跳过更新")
        return slot

    slot.state = new_state
    slot.updated_at = datetime.utcnow()

    history = SlotHistory(
        slot_id_fk=slot.id,
        slot_id=slot.slot_id,
        from_state=old_state,
        to_state=new_state,
        reason=reason,
        event_type=event_type
    )

    db.add(history)
    db.commit()
    db.refresh(slot)

    print(f"状态更新成功: {slot.slot_id} {old_state} -> {new_state}")
    return slot


# =========================
# 4. 批量插入 100 个 Slot
# =========================
def bulk_create_100_slots(db: Session):
    existing_count = db.query(Slot).count()
    if existing_count > 0:
        print(f"数据库已有 {existing_count} 条 Slot，跳过初始化")
        return

    zone_definitions = {
        "Zone-A": ["Lane-A1", "Lane-A2"],
        "Zone-B": ["Lane-B1", "Lane-B2"],
        "Zone-C": ["Lane-C1", "Lane-C2"],
        "Zone-D": ["Lane-D1", "Lane-D2"],
    }

    created_count = 0

    for zone_id, lane_ids in zone_definitions.items():
        for lane_id in lane_ids:
            for i in range(1, 13):  # 8条lane * 12 = 96
                created_count += 1
                slot_id = f"{zone_id[-1]}-{lane_id[-1]}-{i:02d}"
                slot = Slot(
                    slot_id=f"Slot-{slot_id}",
                    zone_id=zone_id,
                    lane_id=lane_id,
                    slot_type="NORMAL" if i <= 10 else "CHARGING",
                    state="FREE"
                )
                db.add(slot)

    # 补到100个
    for i in range(created_count + 1, 101):
        slot = Slot(
            slot_id=f"Slot-X-{i:02d}",
            zone_id="Zone-X",
            lane_id="Lane-X1",
            slot_type="VIP",
            state="FREE"
        )
        db.add(slot)

    db.commit()

    all_slots = db.query(Slot).all()
    for slot in all_slots:
        history = SlotHistory(
            slot_id_fk=slot.id,
            slot_id=slot.slot_id,
            from_state="NONE",
            to_state=slot.state,
            reason="INITIAL_CREATE",
            event_type="INIT"
        )
        db.add(history)

    db.commit()
    print(f"已初始化 {len(all_slots)} 个 Slot")