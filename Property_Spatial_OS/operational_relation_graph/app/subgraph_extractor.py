# 不要把全图交给决策器，只抽取 Case 相关子图。
from sqlalchemy.orm import Session
from .models import Case, Event, Task, SceneNode, SceneEdge


IMPORTANT_RELATIONS = {
    "observes",
    "supports",
    "occupies",
    "near",
    "contains",
    "reachable_by",
    "verified",
    "controls",
    "produces",
    "impacts",
}


def extract_case_subgraph(db: Session, case_id: str, max_nodes: int = 50):
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise ValueError("Case not found")

    seed_node_ids = set()

    if case.target_node_id:
        seed_node_ids.add(case.target_node_id)

    seed_node_ids.add(f"case:{case.case_id}")

    events = db.query(Event).filter(Event.event_id == case.source_event_id).all()
    for e in events:
        seed_node_ids.add(f"event:{e.event_id}")
        if e.source_node_id:
            seed_node_ids.add(e.source_node_id)
        if e.target_node_id:
            seed_node_ids.add(e.target_node_id)

    tasks = db.query(Task).filter(Task.case_id == case.case_id).all()
    for t in tasks:
        seed_node_ids.add(f"task:{t.task_id}")
        if t.target_node_id:
            seed_node_ids.add(t.target_node_id)

    edges = db.query(SceneEdge).filter(
        SceneEdge.relation_type.in_(IMPORTANT_RELATIONS)
    ).all()

    selected_edges = []
    selected_node_ids = set(seed_node_ids)

    for edge in edges:
        if edge.source_node_id in seed_node_ids or edge.target_node_id in seed_node_ids:
            selected_edges.append(edge)
            selected_node_ids.add(edge.source_node_id)
            selected_node_ids.add(edge.target_node_id)

        if len(selected_node_ids) >= max_nodes:
            break

    nodes = db.query(SceneNode).filter(
        SceneNode.node_id.in_(selected_node_ids)
    ).all()

    return {
        "case": {
            "case_id": case.case_id,
            "case_type": case.case_type,
            "state": case.state,
            "confidence": case.confidence,
            "target_node_id": case.target_node_id,
        },
        "nodes": [
            {
                "node_id": n.node_id,
                "node_type": n.node_type,
                "name": n.name,
                "zone": n.zone,
                "state": n.state,
                "confidence": n.confidence,
                "attrs": n.attrs,
            }
            for n in nodes
        ],
        "edges": [
            {
                "edge_id": e.edge_id,
                "source_node_id": e.source_node_id,
                "target_node_id": e.target_node_id,
                "relation_type": e.relation_type,
                "relation_state": e.relation_state,
                "confidence": e.confidence,
                "evidence_count": e.evidence_count,
                "created_by": e.created_by,
            }
            for e in selected_edges
        ],
    }