from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import SceneNode, SceneEdge, Event, Case, Task, TaskOutcome, Executor, AuditLog
from .schemas import SceneNodeCreate, SceneEdgeCreate, EventCreate, TaskOutcomeCreate
from .scene_graph import upsert_node, add_edge, get_neighborhood
from .case_engine import ingest_event_and_create_case, handle_task_outcome
from .scheduler import run_scheduler

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="EboTech Operational Scene Graph Twin",
    version="5.0.0"
)


@app.get("/")
def root():
    return {
        "message": "Operational Scene Graph Twin is running"
    }


@app.post("/scene/nodes")
def create_or_update_node(payload: SceneNodeCreate, db: Session = Depends(get_db)):
    node = upsert_node(db, payload)
    return {
        "node_id": node.node_id,
        "node_type": node.node_type,
        "state": node.state
    }


@app.post("/scene/edges")
def create_edge(payload: SceneEdgeCreate, db: Session = Depends(get_db)):
    edge = add_edge(db, payload)
    return {
        "edge_id": edge.edge_id,
        "relation_type": edge.relation_type
    }


@app.get("/scene/nodes")
def list_nodes(db: Session = Depends(get_db)):
    return db.query(SceneNode).all()


@app.get("/scene/edges")
def list_edges(db: Session = Depends(get_db)):
    return db.query(SceneEdge).all()


@app.get("/scene/neighborhood/{node_id:path}")
def node_neighborhood(node_id: str, db: Session = Depends(get_db)):
    return get_neighborhood(db, node_id)


@app.post("/events/ingest")
def ingest_event(payload: EventCreate, db: Session = Depends(get_db)):
    return ingest_event_and_create_case(db, payload)


@app.get("/events")
def list_events(db: Session = Depends(get_db)):
    return db.query(Event).order_by(Event.id.desc()).all()


@app.get("/cases")
def list_cases(db: Session = Depends(get_db)):
    return db.query(Case).order_by(Case.id.desc()).all()


@app.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.id.desc()).all()


@app.post("/scheduler/run")
def scheduler_run(db: Session = Depends(get_db)):
    return run_scheduler(db)


@app.post("/tasks/outcome")
def submit_task_outcome(payload: TaskOutcomeCreate, db: Session = Depends(get_db)):
    try:
        return handle_task_outcome(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/outcomes")
def list_outcomes(db: Session = Depends(get_db)):
    return db.query(TaskOutcome).order_by(TaskOutcome.id.desc()).all()


@app.get("/executors")
def list_executors(db: Session = Depends(get_db)):
    return db.query(Executor).all()


@app.get("/audit")
def list_audit(db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.id.desc()).all()


@app.get("/replay/{entity_type}/{entity_id:path}")
def replay(entity_type: str, entity_id: str, db: Session = Depends(get_db)):
    return db.query(AuditLog).filter(
        AuditLog.entity_type == entity_type,
        AuditLog.entity_id == entity_id
    ).order_by(AuditLog.id.asc()).all()