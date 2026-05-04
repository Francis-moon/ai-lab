from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import SceneNode, SceneEdge, Event, Case, Task, TaskOutcome, Executor, AuditLog, EventCorrelation, SLAViolation, MapPatch, FeedbackRecord, RiskProfile
from .schemas import SceneNodeCreate, SceneEdgeCreate, EventCreate, TaskOutcomeCreate, FeedbackCreate, MapPatchCreate
from .sla_engine import check_task_sla
from .feedback_engine import submit_feedback
from .map_patch import apply_map_patch, reject_map_patch, propose_map_patch
from .metrics_engine import get_operational_metrics, get_top_risk_nodes
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


@app.post("/sla/check")
def sla_check_api(db: Session = Depends(get_db)):
    return check_task_sla(db)


@app.get("/correlations")
def list_correlations(db: Session = Depends(get_db)):
    return db.query(EventCorrelation).order_by(EventCorrelation.id.desc()).all()


@app.get("/sla/violations")
def list_sla_violations(db: Session = Depends(get_db)):
    return db.query(SLAViolation).order_by(SLAViolation.id.desc()).all()


@app.post("/feedback")
def submit_feedback_api(payload: FeedbackCreate, db: Session = Depends(get_db)):
    try:
        return submit_feedback(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/feedback")
def list_feedback(db: Session = Depends(get_db)):
    return db.query(FeedbackRecord).order_by(FeedbackRecord.id.desc()).all()


@app.post("/map-patches")
def propose_map_patch_api(payload: MapPatchCreate, db: Session = Depends(get_db)):
    patch = propose_map_patch(
        db=db,
        target_node_id=payload.target_node_id,
        patch_type=payload.patch_type,
        payload=payload.payload,
        source_case_id=payload.source_case_id,
        proposed_by=payload.proposed_by
    )

    return {
        "patch_id": patch.patch_id,
        "status": patch.status
    }


@app.get("/map-patches")
def list_map_patches(db: Session = Depends(get_db)):
    return db.query(MapPatch).order_by(MapPatch.id.desc()).all()


@app.post("/map-patches/{patch_id}/apply")
def apply_map_patch_api(patch_id: str, db: Session = Depends(get_db)):
    try:
        return apply_map_patch(db, patch_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/map-patches/{patch_id}/reject")
def reject_map_patch_api(patch_id: str, reason: str, db: Session = Depends(get_db)):
    try:
        return reject_map_patch(db, patch_id, reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/metrics")
def metrics_api(db: Session = Depends(get_db)):
    return get_operational_metrics(db)


@app.get("/risk-profiles")
def risk_profiles_api(db: Session = Depends(get_db)):
    return get_top_risk_nodes(db)