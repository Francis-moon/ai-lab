# 初始化一些测试数据
from .db import SessionLocal, engine, Base
from .models import Slot


def seed_data():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    existing_count = db.query(Slot).count()
    if existing_count > 0:
        db.close()
        print("Data already exists. Skip seeding.")
        return

    sample_slots = [
        Slot(slot_id="A-001", zone="A", state="free"),
        Slot(slot_id="A-002", zone="A", state="occupied"),
        Slot(slot_id="A-003", zone="A", state="illegal"),
        Slot(slot_id="B-001", zone="B", state="free"),
        Slot(slot_id="B-002", zone="B", state="blocked"),
        Slot(slot_id="B-003", zone="B", state="free"),
        Slot(slot_id="C-001", zone="C", state="occupied"),
        Slot(slot_id="C-002", zone="C", state="free"),
        Slot(slot_id="C-003", zone="C", state="free"),
    ]

    db.add_all(sample_slots)
    db.commit()
    db.close()
    print("Seed data inserted successfully.")


if __name__ == "__main__":
    seed_data()