from .database import Base, engine, SessionLocal
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
        ])

    if db.query(ZoneState).count() == 0:
        db.add_all([
            ZoneState(zone="A", heat=3, status="normal", active_event_count=0),
            ZoneState(zone="B", heat=2, status="normal", active_event_count=0),
        ])

    if db.query(Executor).count() == 0:
        db.add_all([
            Executor(
                executor_id="robot-A-1",
                executor_type="robot",
                zone="A",
                status="idle",
                battery_level=80,
                can_handle="recheck_slot,capture_evidence,verify_clearance,charge_robot",
                online=True
            ),
            Executor(
                executor_id="robot-B-1",
                executor_type="robot",
                zone="B",
                status="idle",
                battery_level=15,
                can_handle="recheck_slot,capture_evidence,verify_clearance,charge_robot",
                online=True
            ),
            Executor(
                executor_id="human-A-1",
                executor_type="human",
                zone="A",
                status="idle",
                battery_level=None,
                can_handle="clear_blocked_lane,manual_review,recheck_slot",
                online=True
            ),
            Executor(
                executor_id="cloud-A-1",
                executor_type="cloud_operator",
                zone="A",
                status="idle",
                battery_level=None,
                can_handle="remote_verify,manual_review,capture_evidence",
                online=True
            ),
        ])

    db.commit()
    db.close()
    print("Seed completed.")


if __name__ == "__main__":
    seed_data()