from typing import List
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Event, Task, ZoneState, Executor, AuditLog
from .schemas import (
    EventCreate,
    EventResponse,
    TaskResponse,
    ZoneResponse,
    ExecutorResponse,
    AuditResponse
)
from .agent import process_event
from .scheduler import run_scheduler, complete_task, fail_task

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="EboTECH Operational Twin Kernel",
    version="4.0.0"
)


@app.get("/")
def root():
    return {"message": "Operational Twin Kernel is running"}


@app.post("/agent/process-event")
def process_event_api(payload: EventCreate, db: Session = Depends(get_db)):
    return process_event(db, payload)


@app.get("/events", response_model=List[EventResponse])
def list_events(db: Session = Depends(get_db)):
    return db.query(Event).order_by(Event.id.desc()).all()


@app.get("/tasks", response_model=List[TaskResponse])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.chain_id, Task.step_order).all()


@app.post("/scheduler/run")
def scheduler_run_api(db: Session = Depends(get_db)):
    return run_scheduler(db)


@app.post("/tasks/{task_id}/complete")
def complete_task_api(task_id: str, db: Session = Depends(get_db)):
    try:
        return complete_task(db, task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/tasks/{task_id}/fail")
def fail_task_api(task_id: str, db: Session = Depends(get_db)):
    try:
        return fail_task(db, task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/zones", response_model=List[ZoneResponse])
def list_zones(db: Session = Depends(get_db)):
    return db.query(ZoneState).all()


@app.get("/executors", response_model=List[ExecutorResponse])
def list_executors(db: Session = Depends(get_db)):
    return db.query(Executor).all()


@app.get("/audit", response_model=List[AuditResponse])
def list_audit(db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.id.desc()).all()


@app.get("/replay/{entity_type}/{entity_id}", response_model=List[AuditResponse])
def replay_entity(entity_type: str, entity_id: str, db: Session = Depends(get_db)):
    return db.query(AuditLog).filter(
        AuditLog.entity_type == entity_type,
        AuditLog.entity_id == entity_id
    ).order_by(AuditLog.id.asc()).all()