from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import (
    SceneNode,
    SceneEdge,
    RelationEvidence,
    Event,
    Case,
    Task,
    TaskOutcome,
    Executor,
    AuditLog
)
from .schemas import (
    SceneNodeCreate,
    SceneEdgeCreate,
    EventCreate,
    TaskOutcomeCreate
)
from .scene_graph import (
    upsert_node,
    upsert_relation,
    get_neighborhood,
    get_case_relevant_subgraph
)
from .case_engine import (
    ingest_event_and_create_case,
    handle_task_outcome
)
from .scheduler import run_scheduler

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Yibo Operational Relation Graph",
    version="3.0.0"
)


@app.get("/")
def root():
    return {
        "message": "V3 Operational Relation Graph is running"
    }


# -------------------------
# Scene Graph API
# -------------------------
@app.post("/scene/nodes")
def create_or_update_node(payload: SceneNodeCreate, db: Session = Depends(get_db)):
    node = upsert_node(db, payload)

    return {
        "node_id": node.node_id,
        "node_type": node.node_type,
        "state": node.state,
        "confidence": node.confidence
    }


@app.get("/scene/nodes")
def list_nodes(db: Session = Depends(get_db)):
    return db.query(SceneNode).all()


@app.post("/scene/edges")
def create_or_update_edge(payload: SceneEdgeCreate, db: Session = Depends(get_db)):
    edge = upsert_relation(
        db=db,
        source_node_id=payload.source_node_id,
        target_node_id=payload.target_node_id,
        relation_type=payload.relation_type,
        relation_state=payload.relation_state,
        confidence=payload.confidence,
        created_by=payload.created_by,
        source_event_id=payload.source_event_id,
        attrs=payload.attrs,
        evidence_signal="neutral",
        evidence_note="manual edge upsert"
    )

    return {
        "edge_id": edge.edge_id,
        "relation_type": edge.relation_type,
        "relation_state": edge.relation_state,
        "confidence": edge.confidence
    }


@app.get("/scene/edges")
def list_edges(db: Session = Depends(get_db)):
    return db.query(SceneEdge).all()


@app.get("/scene/evidence")
def list_relation_evidence(db: Session = Depends(get_db)):
    return db.query(RelationEvidence).order_by(RelationEvidence.id.desc()).all()


@app.get("/scene/neighborhood/{node_id:path}")
def neighborhood(node_id: str, db: Session = Depends(get_db)):
    return get_neighborhood(db, node_id)


@app.get("/scene/case-subgraph/{case_id}")
def case_subgraph(case_id: str, db: Session = Depends(get_db)):
    try:
        return get_case_relevant_subgraph(db, case_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -------------------------
# Event / Case API
# -------------------------
@app.post("/events/ingest")
def ingest_event(payload: EventCreate, db: Session = Depends(get_db)):
    return ingest_event_and_create_case(db, payload)


@app.get("/events")
def list_events(db: Session = Depends(get_db)):
    return db.query(Event).order_by(Event.id.desc()).all()


@app.get("/cases")
def list_cases(db: Session = Depends(get_db)):
    return db.query(Case).order_by(Case.id.desc()).all()


@app.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.case_id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return case


# -------------------------
# Task / Outcome API
# -------------------------
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


# -------------------------
# Executor API
# -------------------------
@app.get("/executors")
def list_executors(db: Session = Depends(get_db)):
    return db.query(Executor).all()


# -------------------------
# Audit / Replay API
# -------------------------
@app.get("/audit")
def list_audit(db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.id.desc()).all()


@app.get("/replay/{entity_type}/{entity_id:path}")
def replay(entity_type: str, entity_id: str, db: Session = Depends(get_db)):
    return db.query(AuditLog).filter(
        AuditLog.entity_type == entity_type,
        AuditLog.entity_id == entity_id
    ).order_by(AuditLog.id.asc()).all()