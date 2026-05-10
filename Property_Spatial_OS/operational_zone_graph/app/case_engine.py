from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .models import Event, Case, Task, TaskOutcome, FunctionalZone
from .audit import write_audit
from .zone_graph import update_zone_state
from .constants import (
    CASE_SUSPECTED,
    CASE_VERIFYING,
    CASE_CONFIRMED,
    CASE_ESCALATED,
    CASE_CLOSED,
    TASK_CREATED,
    TASK_DONE
)


def find_related_open_case(db: Session, event: Event):
    since = datetime.utcnow() - timedelta(minutes=10)

    return db.query(Case).filter(
        Case.case_type == event.event_type,
        Case.zone_id == event.zone_id,
        Case.target_node_id == event.target_node_id,
        Case.state != CASE_CLOSED,
        Case.created_at >= since
    ).first()


def get_zone_policy(db: Session, zone_id: str):
    zone = db.query(FunctionalZone).filter(
        FunctionalZone.zone_id == zone_id
    ).first()

    if not zone:
        return {}

    return zone.policy or {}


def create_task(
    db: Session,
    case: Case,
    task_type: str,
    priority: str,
    sla_minutes: int,
    fallback_chain: str
):
    task_id = f"{case.case_id}-{task_type}-{int(datetime.utcnow().timestamp())}"

    task = Task(
        task_id=task_id,
        case_id=case.case_id,
        task_type=task_type,
        zone_id=case.zone_id,
        target_node_id=case.target_node_id,
        priority=priority,
        sla_minutes=sla_minutes,
        fallback_chain=fallback_chain,
        status=TASK_CREATED
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    case.current_task_id = task.task_id
    case.updated_at = datetime.utcnow()
    db.commit()

    update_zone_state(db, case.zone_id)

    write_audit(
        db,
        "task",
        task.task_id,
        "task_created",
        f"type={task.task_type}, zone={task.zone_id}, case={case.case_id}"
    )

    return task


def decide_initial_task(db: Session, case: Case):
    policy = get_zone_policy(db, case.zone_id)

    if case.case_type == "illegal_parking_detected":
        case.state = CASE_VERIFYING
        db.commit()

        return create_task(
            db=db,
            case=case,
            task_type="remote_verify",
            priority=policy.get("illegal_parking_priority", "high"),
            sla_minutes=policy.get("illegal_parking_sla", 3),
            fallback_chain=policy.get(
                "illegal_parking_fallback",
                "cloud_operator,robot,human"
            )
        )

    if case.case_type == "lane_blocked_detected":
        case.state = CASE_CONFIRMED
        case.severity = "critical"
        db.commit()

        return create_task(
            db=db,
            case=case,
            task_type="clear_blocked_lane",
            priority="critical",
            sla_minutes=policy.get("blocked_lane_sla", 3),
            fallback_chain=policy.get(
                "blocked_lane_fallback",
                "human,robot,cloud_operator"
            )
        )

    if case.case_type == "device_fault_detected":
        case.state = CASE_VERIFYING
        case.severity = "high"
        db.commit()

        return create_task(
            db=db,
            case=case,
            task_type="device_diagnosis",
            priority="high",
            sla_minutes=policy.get("device_fault_sla", 10),
            fallback_chain=policy.get(
                "device_fault_fallback",
                "human,cloud_operator"
            )
        )

    return create_task(
        db=db,
        case=case,
        task_type="manual_review",
        priority="medium",
        sla_minutes=15,
        fallback_chain="cloud_operator,human"
    )


def ingest_event(db: Session, payload):
    event = Event(
        event_id=payload.event_id,
        event_type=payload.event_type,
        source=payload.source,
        source_node_id=payload.source_node_id,
        target_node_id=payload.target_node_id,
        zone_id=payload.zone_id,
        confidence=payload.confidence,
        status="new"
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    related_case = find_related_open_case(db, event)

    if related_case:
        event.status = "correlated"
        related_case.confidence = min(99, related_case.confidence + 10)
        related_case.updated_at = datetime.utcnow()
        db.commit()

        update_zone_state(db, event.zone_id)

        write_audit(
            db,
            "event",
            event.event_id,
            "event_correlated",
            f"case={related_case.case_id}, zone={event.zone_id}"
        )

        return {
            "status": "correlated_to_existing_case",
            "event_id": event.event_id,
            "case_id": related_case.case_id,
            "zone_id": event.zone_id
        }

    case = Case(
        case_id=f"case-{event.event_id}",
        case_type=event.event_type,
        zone_id=event.zone_id,
        target_node_id=event.target_node_id,
        state=CASE_SUSPECTED,
        severity="medium",
        confidence=event.confidence,
        source_event_id=event.event_id
    )

    db.add(case)
    db.commit()
    db.refresh(case)

    task = decide_initial_task(db, case)

    update_zone_state(db, event.zone_id)

    write_audit(
        db,
        "case",
        case.case_id,
        "case_created",
        f"type={case.case_type}, zone={case.zone_id}, task={task.task_id}"
    )

    return {
        "status": "case_created",
        "event_id": event.event_id,
        "case_id": case.case_id,
        "zone_id": case.zone_id,
        "initial_task_id": task.task_id
    }


def handle_task_outcome(db: Session, payload):
    task = db.query(Task).filter(
        Task.task_id == payload.task_id
    ).first()

    if not task:
        raise ValueError("Task not found")

    case = db.query(Case).filter(
        Case.case_id == task.case_id
    ).first()

    if not case:
        raise ValueError("Case not found")

    outcome = TaskOutcome(
        outcome_id=payload.outcome_id,
        task_id=payload.task_id,
        case_id=case.case_id,
        outcome_type=payload.outcome_type,
        confidence=payload.confidence,
        note=payload.note,
        evidence_url=payload.evidence_url,
        created_by=payload.created_by
    )

    db.add(outcome)

    task.status = TASK_DONE
    task.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(outcome)

    decision = decide_next_step(db, case, task, outcome)

    update_zone_state(db, case.zone_id)

    write_audit(
        db,
        "case",
        case.case_id,
        "task_outcome_handled",
        f"task={task.task_id}, outcome={outcome.outcome_type}, decision={decision}"
    )

    return decision


def close_case(db: Session, case: Case, reason: str):
    case.state = CASE_CLOSED
    case.current_task_id = None
    case.updated_at = datetime.utcnow()

    db.commit()

    update_zone_state(db, case.zone_id)

    write_audit(
        db,
        "case",
        case.case_id,
        "case_closed",
        reason
    )

    return {
        "status": "case_closed",
        "case_id": case.case_id,
        "zone_id": case.zone_id,
        "reason": reason
    }


def decide_next_step(db: Session, case: Case, task: Task, outcome: TaskOutcome):
    policy = get_zone_policy(db, case.zone_id)

    if task.task_type == "remote_verify":
        if outcome.outcome_type == "false_alarm":
            return close_case(db, case, "remote_verify_false_alarm")

        if outcome.outcome_type == "confirmed_illegal":
            case.state = CASE_CONFIRMED
            case.confidence = max(case.confidence, outcome.confidence)
            db.commit()

            next_task = create_task(
                db=db,
                case=case,
                task_type="capture_evidence",
                priority="high",
                sla_minutes=policy.get("evidence_sla", 5),
                fallback_chain="robot,human,cloud_operator"
            )

            return {
                "status": "next_task_created",
                "next_task_id": next_task.task_id
            }

        if outcome.outcome_type == "low_confidence":
            next_task = create_task(
                db=db,
                case=case,
                task_type="robot_recheck",
                priority="high",
                sla_minutes=policy.get("robot_recheck_sla", 8),
                fallback_chain="robot,human"
            )

            return {
                "status": "next_task_created",
                "next_task_id": next_task.task_id
            }

    if task.task_type == "robot_recheck":
        if outcome.outcome_type == "cleared":
            return close_case(db, case, "robot_recheck_cleared")

        if outcome.outcome_type == "still_present":
            case.state = CASE_CONFIRMED
            case.confidence = max(case.confidence, outcome.confidence)
            db.commit()

            next_task = create_task(
                db=db,
                case=case,
                task_type="capture_evidence",
                priority="high",
                sla_minutes=5,
                fallback_chain="robot,human"
            )

            return {
                "status": "next_task_created",
                "next_task_id": next_task.task_id
            }

    if task.task_type == "capture_evidence":
        if outcome.outcome_type == "evidence_captured":
            next_task = create_task(
                db=db,
                case=case,
                task_type="notify_property",
                priority="medium",
                sla_minutes=10,
                fallback_chain="cloud_operator,human"
            )

            return {
                "status": "next_task_created",
                "next_task_id": next_task.task_id
            }

    if task.task_type == "clear_blocked_lane":
        if outcome.outcome_type == "cleared":
            return close_case(db, case, "lane_cleared")

        if outcome.outcome_type == "failed":
            case.state = CASE_ESCALATED
            case.severity = "critical"
            db.commit()

            next_task = create_task(
                db=db,
                case=case,
                task_type="supervisor_escalation",
                priority="critical",
                sla_minutes=2,
                fallback_chain="human,cloud_operator"
            )

            return {
                "status": "escalated",
                "next_task_id": next_task.task_id
            }

    if task.task_type == "device_diagnosis":
        if outcome.outcome_type == "device_ok":
            return close_case(db, case, "device_ok")

        if outcome.outcome_type == "device_fault_confirmed":
            next_task = create_task(
                db=db,
                case=case,
                task_type="repair_dispatch",
                priority="high",
                sla_minutes=30,
                fallback_chain="human"
            )

            return {
                "status": "repair_task_created",
                "next_task_id": next_task.task_id
            }

    if task.task_type == "notify_property":
        if outcome.outcome_type == "notified":
            return close_case(db, case, "property_notified")

    return {
        "status": "no_rule_matched",
        "case_id": case.case_id,
        "zone_id": case.zone_id
    }