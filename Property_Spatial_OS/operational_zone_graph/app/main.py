from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import (
    FunctionalZone,
    ZoneTopologyEdge,
    ZoneMember,
    SceneNode,
    Event,
    Case,
    Task,
    TaskOutcome,
    Executor,
    AuditLog
)
from .schemas import (
    ZoneCreate,
    ZoneTopologyCreate,
    SceneNodeCreate,
    ZoneMemberCreate,
    EventCreate,
    TaskOutcomeCreate
)
from .zone_graph import (
    upsert_zone,
    add_zone_topology_edge,
    upsert_scene_node,
    link_node_to_zone,
    get_zone_context,
    update_zone_state
)
from .case_engine import ingest_event, handle_task_outcome
from .scheduler import run_scheduler

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Ebotech Operational Zone Graph",
    version="4.0.0"
)


@app.get("/")
def root():
    return {
        "message": "V4 operational_zone-graph is running"
    }


# -------------------------
# Zone Graph API
# -------------------------
@app.post("/zones")
def create_or_update_zone(payload: ZoneCreate, db: Session = Depends(get_db)):
    zone = upsert_zone(db, payload)

    return {
        "zone_id": zone.zone_id,
        "name": zone.name,
        "zone_type": zone.zone_type,
        "state": zone.state,
        "heat": zone.heat
    }


@app.get("/zones")
def list_zones(db: Session = Depends(get_db)):
    return db.query(FunctionalZone).all()


@app.get("/zones/{zone_id:path}")
def get_zone(zone_id: str, db: Session = Depends(get_db)):
    zone = db.query(FunctionalZone).filter(
        FunctionalZone.zone_id == zone_id
    ).first()

    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    return zone


@app.post("/zones/{zone_id:path}/refresh-state")
def refresh_zone_state(zone_id: str, db: Session = Depends(get_db)):
    try:
        return update_zone_state(db, zone_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/zone-topology")
def create_zone_topology(payload: ZoneTopologyCreate, db: Session = Depends(get_db)):
    edge = add_zone_topology_edge(db, payload)

    return {
        "edge_id": edge.edge_id,
        "source_zone_id": edge.source_zone_id,
        "target_zone_id": edge.target_zone_id,
        "relation_type": edge.relation_type
    }


@app.get("/zone-topology")
def list_zone_topology(db: Session = Depends(get_db)):
    return db.query(ZoneTopologyEdge).all()


@app.get("/zones/{zone_id:path}/context")
def zone_context(zone_id: str, db: Session = Depends(get_db)):
    try:
        return get_zone_context(db, zone_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -------------------------
# Scene Node / Zone Member API
# -------------------------
@app.post("/scene/nodes")
def create_or_update_node(payload: SceneNodeCreate, db: Session = Depends(get_db)):
    node = upsert_scene_node(db, payload)

    return {
        "node_id": node.node_id,
        "node_type": node.node_type,
        "zone_id": node.zone_id,
        "state": node.state
    }


@app.get("/scene/nodes")
def list_nodes(db: Session = Depends(get_db)):
    return db.query(SceneNode).all()


@app.post("/zone-members")
def create_zone_member(payload: ZoneMemberCreate, db: Session = Depends(get_db)):
    member = link_node_to_zone(db, payload)

    return {
        "zone_id": member.zone_id,
        "node_id": member.node_id,
        "role": member.role
    }


@app.get("/zone-members")
def list_zone_members(db: Session = Depends(get_db)):
    return db.query(ZoneMember).all()


# -------------------------
# Event / Case API
# -------------------------
@app.post("/events/ingest")
def ingest_event_api(payload: EventCreate, db: Session = Depends(get_db)):
    return ingest_event(db, payload)


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
# Task / Scheduler API
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
# Audit API
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