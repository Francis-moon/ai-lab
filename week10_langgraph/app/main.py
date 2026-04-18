from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Slot, Event, Task
from .schemas import (
    SlotCreate,
    SlotResponse,
    SlotUpdateState,
    EventCreate,
    EventResponse,
    TaskCreate,
    TaskResponse,
)
from .agent import agent_app

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="EboTech Parking Agent API",
    description="Event-Task-Agent demo for parking operations",
    version="2.0.0"
)


@app.get("/")
def root():
    return {"message": "EboTech Parking Agent API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


# -------------------------
# Slot API
# -------------------------
@app.get("/slots", response_model=List[SlotResponse])
def list_slots(
    zone: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
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

    slot = Slot(
        slot_id=payload.slot_id,
        zone=payload.zone,
        state=payload.state
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@app.put("/slots/{slot_id}/state", response_model=SlotResponse)
def update_slot_state(slot_id: str, payload: SlotUpdateState, db: Session = Depends(get_db)):
    allowed_states = {"free", "occupied", "illegal", "blocked"}
    if payload.state not in allowed_states:
        raise HTTPException(status_code=400, detail="Invalid state")

    slot = db.query(Slot).filter(Slot.slot_id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    slot.state = payload.state
    db.commit()
    db.refresh(slot)
    return slot


# -------------------------
# Event API
# -------------------------
@app.post("/events", response_model=EventResponse)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    existing = db.query(Event).filter(Event.event_id == payload.event_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Event already exists")

    event = Event(
        event_id=payload.event_id,
        event_type=payload.event_type,
        slot_id=payload.slot_id,
        zone=payload.zone,
        source=payload.source,
        status="new"
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@app.get("/events", response_model=List[EventResponse])
def list_events(db: Session = Depends(get_db)):
    return db.query(Event).all()


@app.put("/events/{event_id}/processed", response_model=EventResponse)
def mark_event_processed_api(event_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event.status = "processed"
    db.commit()
    db.refresh(event)
    return event


# -------------------------
# Task API
# -------------------------
@app.post("/tasks", response_model=TaskResponse)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    existing = db.query(Task).filter(Task.task_id == payload.task_id).first()
    if existing:
        return existing

    task = Task(
        task_id=payload.task_id,
        task_type=payload.task_type,
        slot_id=payload.slot_id,
        zone=payload.zone,
        assignee=payload.assignee,
        priority=payload.priority,
        status="created"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tasks", response_model=List[TaskResponse])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).all()


# -------------------------
# Agent API
# -------------------------
@app.post("/agent/process-event")
def process_event_with_agent(payload: EventCreate, db: Session = Depends(get_db)):
    existing = db.query(Event).filter(Event.event_id == payload.event_id).first()
    if not existing:
        event = Event(
            event_id=payload.event_id,
            event_type=payload.event_type,
            slot_id=payload.slot_id,
            zone=payload.zone,
            source=payload.source,
            status="new"
        )
        db.add(event)
        db.commit()

    state = {
        "event_id": payload.event_id,
        "event_type": payload.event_type,
        "slot_id": payload.slot_id,
        "zone": payload.zone,
        "source": payload.source,
        "current_slot_state": None,
        "decision": None,
        "task_result": None,
        "slot_update_result": None,
        "final_result": None,
        "error": None,
    }

    result = agent_app.invoke(state)
    return result["final_result"]