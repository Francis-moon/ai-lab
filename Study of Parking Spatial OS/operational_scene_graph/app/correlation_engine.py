from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .models import Event, Case, EventCorrelation, SceneEdge
from .confidence import normalize_confidence, fuse_confidence
from .audit import write_audit


CORRELATION_WINDOW_MINUTES = 10
CORRELATION_THRESHOLD = 60


def graph_distance_score(db: Session, node_a: str, node_b: str) -> int:
    if not node_a or not node_b:
        return 0

    if node_a == node_b:
        return 60

    direct = db.query(SceneEdge).filter(
        SceneEdge.source_node_id == node_a,
        SceneEdge.target_node_id == node_b
    ).first()

    reverse = db.query(SceneEdge).filter(
        SceneEdge.source_node_id == node_b,
        SceneEdge.target_node_id == node_a
    ).first()

    if direct or reverse:
        return 35

    return 0


def event_case_correlation_score(db: Session, event: Event, case: Case) -> tuple[int, list[str]]:
    score = 0
    reasons = []

    if event.zone == case.zone:
        score += 20
        reasons.append("same_zone")

    if event.target_node_id and case.target_node_id:
        g_score = graph_distance_score(db, event.target_node_id, case.target_node_id)
        score += g_score
        if g_score >= 60:
            reasons.append("same_target_node")
        elif g_score >= 35:
            reasons.append("nearby_graph_node")

    if event.event_type == case.case_type:
        score += 25
        reasons.append("same_event_type")

    if event.confidence >= 80:
        score += 10
        reasons.append("high_confidence_signal")

    return score, reasons


def find_best_related_case(db: Session, event: Event):
    since = datetime.utcnow() - timedelta(minutes=CORRELATION_WINDOW_MINUTES)

    candidates = db.query(Case).filter(
        Case.zone == event.zone,
        Case.state != "closed",
        Case.created_at >= since
    ).all()

    best_case = None
    best_score = 0
    best_reasons = []

    for case in candidates:
        score, reasons = event_case_correlation_score(db, event, case)
        if score > best_score:
            best_score = score
            best_case = case
            best_reasons = reasons

    if best_score >= CORRELATION_THRESHOLD:
        return best_case, best_score, best_reasons

    return None, best_score, best_reasons


def correlate_event_to_case(db: Session, event: Event):
    case, score, reasons = find_best_related_case(db, event)

    if not case:
        return None

    correlation = EventCorrelation(
        correlation_id=f"corr-{event.event_id}-{case.case_id}",
        event_id=event.event_id,
        case_id=case.case_id,
        relation_type="supports",
        score=score,
        reason=",".join(reasons)
    )

    db.add(correlation)

    incoming_confidence = normalize_confidence(event.confidence, event.source)
    case.confidence = fuse_confidence(case.confidence, incoming_confidence)

    db.commit()

    write_audit(
        db,
        "case",
        case.case_id,
        "event_correlated",
        f"event={event.event_id}, score={score}, reasons={reasons}, confidence={case.confidence}"
    )

    return case
    