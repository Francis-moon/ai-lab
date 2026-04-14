from db import Base, engine, SessionLocal
from crud import (
    get_all_slots,
    get_free_slots_by_zone,
    get_slot_histories,
)
from seed import seed_data, simulate_status_changes


def print_slots(slots, limit=None):
    print("\n=== Slot列表 ===")
    rows = slots if limit is None else slots[:limit]
    for slot in rows:
        print(slot)
    if limit is not None and len(slots) > limit:
        print(f"... 共 {len(slots)} 条，仅显示前 {limit} 条")


def print_histories(histories):
    print("\n=== 历史记录 ===")
    for h in histories:
        print(
            f"{h.created_at} | {h.slot_id} | "
            f"{h.from_state} -> {h.to_state} | "
            f"reason={h.reason} | event={h.event_type}"
        )


def main():
    # 1. 建表
    Base.metadata.create_all(bind=engine)
    print("数据库和表已就绪")

    db = SessionLocal()

    try:
        # 2. 初始化100个Slot
        seed_data(db)

        # 3. 查询全部Slot
        all_slots = get_all_slots(db)
        print_slots(all_slots, limit=10)

        # 4. 模拟若干状态变化
        simulate_status_changes(db)

        # 5. 查询某区域空闲车位
        free_slots_a = get_free_slots_by_zone(db, "Zone-A")
        print("\n=== Zone-A 空闲车位 ===")
        for slot in free_slots_a[:10]:
            print(slot)
        if len(free_slots_a) > 10:
            print(f"... Zone-A 共 {len(free_slots_a)} 个空闲车位，仅显示前10个")

        # 6. 查询某个车位历史
        histories = get_slot_histories(db, "Slot-A-1-02")
        print_histories(histories)

    finally:
        db.close()


if __name__ == "__main__":
    main()