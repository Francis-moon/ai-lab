from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Slot
from .schemas import SlotCreate, SlotResponse, SlotUpdateState

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Parking Slot API",
    description="A simple FastAPI demo for parking space management",
    version="1.0.0"
)


@app.get("/")
def root():
    return {"message": "Parking Slot API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/slots", response_model=List[SlotResponse])
def list_slots(
    zone: Optional[str] = Query(default=None, description="Filter by zone"),
    state: Optional[str] = Query(default=None, description="Filter by state"),
    db: Session = Depends(get_db)
):
    query = db.query(Slot)

    if zone:
        query = query.filter(Slot.zone == zone)

    if state:
        query = query.filter(Slot.state == state)

    return query.all()


@app.get("/slots/{slot_id}", response_model=SlotResponse)
def get_slot(slot_id: str, db: Session = Depends(get_db)):
    slot = db.query(Slot).filter(Slot.slot_id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    return slot


@app.post("/slots", response_model=SlotResponse)
def create_slot(payload: SlotCreate, db: Session = Depends(get_db)):
    existing = db.query(Slot).filter(Slot.slot_id == payload.slot_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Slot already exists")

    new_slot = Slot(
        slot_id=payload.slot_id,
        zone=payload.zone,
        state=payload.state
    )
    db.add(new_slot)
    db.commit()
    db.refresh(new_slot)
    return new_slot


# 非法停车转工单
@app.post("/tasks/illegal-parking/{slot_id}")
def create_illegal_parking_task(slot_id: str, db: Session = Depends(get_db)):
    slot = db.query(Slot).filter(Slot.slot_id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    if slot.state != "illegal":
        raise HTTPException(status_code=400, detail="Slot is not in illegal state")

    return {
        "task_type": "inspect_illegal_parking",
        "slot_id": slot.slot_id,
        "zone": slot.zone,
        "status": "created"
    }


@app.put("/slots/{slot_id}/state", response_model=SlotResponse)
def update_slot_state(slot_id: str, payload: SlotUpdateState, db: Session = Depends(get_db)):
    allowed_states = {"free", "occupied", "illegal", "blocked"}

    if payload.state not in allowed_states:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state. Allowed states: {sorted(allowed_states)}"
        )

    slot = db.query(Slot).filter(Slot.slot_id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    slot.state = payload.state
    db.commit()
    db.refresh(slot)
    return slot


@app.delete("/slots/{slot_id}")
def delete_slot(slot_id: str, db: Session = Depends(get_db)):
    slot = db.query(Slot).filter(Slot.slot_id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    db.delete(slot)
    db.commit()
    return {"message": f"{slot_id} deleted successfully"}


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    slots = db.query(Slot).all()
    total = len(slots)

    result = {
        "total": total,
        "free": 0,
        "occupied": 0,
        "illegal": 0,
        "blocked": 0
    }

    for slot in slots:
        if slot.state in result:
            result[slot.state] += 1

    return result
