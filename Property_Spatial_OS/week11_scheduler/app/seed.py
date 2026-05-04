from .database import SessionLocal, engine, Base
from .models import Slot, Executor, ZoneState


def seed_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Slot).count() == 0:
        db.add_all([
            Slot(slot_id="A-001", zone="A", state="free"),
            Slot(slot_id="A-002", zone="A", state="occupied"),
            Slot(slot_id="A-003", zone="A", state="illegal"),
            Slot(slot_id="B-001", zone="B", state="free"),
            Slot(slot_id="B-002", zone="B", state="blocked"),
            Slot(slot_id="B-003", zone="B", state="free"),
        ])

    if db.query(Executor).count() == 0:
        db.add_all([
            Executor(
                executor_id="robot-A-1",
                executor_type="robot",
                zone="A",
                status="idle",
                battery_level=80,
                current_task_id=None,
                can_handle="inspect_illegal_parking,recheck_slot,charge_robot",
                online=True
            ),
            Executor(
                executor_id="robot-B-1",
                executor_type="robot",
                zone="B",
                status="idle",
                battery_level=10,
                current_task_id=None,
                can_handle="inspect_illegal_parking,recheck_slot,charge_robot",
                online=True
            ),
            Executor(
                executor_id="human-A-1",
                executor_type="human",
                zone="A",
                status="idle",
                battery_level=None,
                current_task_id=None,
                can_handle="clear_blocked_lane,inspect_illegal_parking,notify_security",
                online=True
            ),
            Executor(
                executor_id="cloud-A-1",
                executor_type="cloud_operator",
                zone="A",
                status="idle",
                battery_level=None,
                current_task_id=None,
                can_handle="notify_driver,remote_verify,inspect_illegal_parking",
                online=True
            ),
        ])

    if db.query(ZoneState).count() == 0:
        db.add_all([
            ZoneState(zone="A", heat=8, status="high_risk"),
            ZoneState(zone="B", heat=5, status="congested"),
            ZoneState(zone="C", heat=2, status="normal"),
        ])

    db.commit()
    db.close()
    print("Seed completed.")
    

if __name__ == "__main__":
    seed_data()