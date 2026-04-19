from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Slot, Event, Task, Executor, ZoneState
from .schemas import (
    SlotCreate, SlotUpdateState, SlotResponse,
    EventCreate, EventResponse,
    TaskCreate, TaskResponse,
    ExecutorResponse, ZoneStateResponse
)
from .agent import agent_app
from .scheduler import schedule_pending_tasks, complete_task, fail_task_with_fallback

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Yibo Week11 Scheduler API",
    description="Multi-executor orchestration demo",
    version="3.0.0"
)


@app.get("/")
def root():
    return {"message": "Week11 Scheduler API is running"}


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
    q = db.query(Slot)
    if zone:
        q = q.filter(Slot.zone == zone)
    if state:
        q = q.filter(Slot.state == state)
    return q.all()


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

    slot = Slot(slot_id=payload.slot_id, zone=payload.zone, state=payload.state)
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@app.put("/slots/{slot_id}/state", response_model=SlotResponse)
def update_slot_state(slot_id: str, payload: SlotUpdateState, db: Session = Depends(get_db)):
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
        return existing

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
def mark_event_processed(event_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.status = "processed"
    db.commit()
    db.refresh(event)
    return event


# -------------------------
# Zone API
# -------------------------
@app.get("/zones", response_model=List[ZoneStateResponse])
def list_zones(db: Session = Depends(get_db)):
    return db.query(ZoneState).all()


@app.get("/zones/{zone}", response_model=ZoneStateResponse)
def get_zone(zone: str, db: Session = Depends(get_db)):
    z = db.query(ZoneState).filter(ZoneState.zone == zone).first()
    if not z:
        raise HTTPException(status_code=404, detail="Zone not found")
    return z


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
        preferred_assignee=payload.preferred_assignee,
        priority=payload.priority,
        sla_minutes=payload.sla_minutes,
        zone_heat=payload.zone_heat,
        fallback_chain=payload.fallback_chain,
        status="created"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tasks", response_model=List[TaskResponse])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).all()


@app.post("/tasks/{task_id}/complete")
def complete_task_api(task_id: str, db: Session = Depends(get_db)):
    try:
        return complete_task(db, task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/tasks/{task_id}/fail")
def fail_task_api(task_id: str, db: Session = Depends(get_db)):
    try:
        return fail_task_with_fallback(db, task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -------------------------
# Executor API
# -------------------------
@app.get("/executors", response_model=List[ExecutorResponse])
def list_executors(db: Session = Depends(get_db)):
    return db.query(Executor).all()


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
        "zone_heat": None,
        "decision": None,
        "task_payload": None,
        "task_result": None,
        "slot_update_result": None,
        "final_result": None,
        "error": None,
    }

    result = agent_app.invoke(state)
    return result["final_result"]


# -------------------------
# Scheduler API
# -------------------------
@app.post("/scheduler/run")
def run_scheduler(db: Session = Depends(get_db)):
    return schedule_pending_tasks(db)