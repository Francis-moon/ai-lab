# 这是核心：不是固定任务链，而是结果驱动的动态状态机
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .models import Event, Case, Task, TaskOutcome, SceneNode
from .audit import write_audit
from .scene_graph import update_node_state, add_edge
from .constants import (
    CASE_SUSPECTED,
    CASE_VERIFYING,
    CASE_CONFIRMED,
    CASE_WAITING,
    CASE_ESCALATED,
    CASE_CLOSED,
    TASK_CREATED
)


def find_related_open_case(db: Session, event):
    since = datetime.utcnow() - timedelta(minutes=10)

    return db.query(Case).filter(
        Case.case_type == event.event_type,
        Case.zone == event.zone,
        Case.target_node_id == event.target_node_id,
        Case.state != CASE_CLOSED,
        Case.created_at >= since
    ).first()


def create_event_node(db: Session, event: Event):
    node = SceneNode(
        node_id=f"event:{event.event_id}",
        node_type="event",
        name=event.event_type,
        zone=event.zone,
        state="new",
        confidence=event.confidence,
        attrs={
            "source": event.source,
            "source_node_id": event.source_node_id,
            "target_node_id": event.target_node_id
        }
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def create_case_node(db: Session, case: Case):
    node = SceneNode(
        node_id=f"case:{case.case_id}",
        node_type="case",
        name=case.case_type,
        zone=case.zone,
        state=case.state,
        confidence=case.confidence,
        attrs={
            "severity": case.severity,
            "target_node_id": case.target_node_id
        }
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


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
        target_node_id=case.target_node_id,
        zone=case.zone,
        priority=priority,
        sla_minutes=sla_minutes,
        fallback_chain=fallback_chain,
        status=TASK_CREATED
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    case.current_task_id = task.task_id
    db.commit()

    task_node = SceneNode(
        node_id=f"task:{task.task_id}",
        node_type="task",
        name=task.task_type,
        zone=task.zone,
        state=task.status,
        confidence=100,
        attrs={
            "case_id": case.case_id,
            "priority": priority,
            "sla_minutes": sla_minutes
        }
    )
    db.add(task_node)
    db.commit()

    edge_payload = type("EdgePayload", (), {
        "edge_id": f"case:{case.case_id}-requires-task:{task.task_id}",
        "source_node_id": f"case:{case.case_id}",
        "target_node_id": f"task:{task.task_id}",
        "relation_type": "requires",
        "confidence": 100,
        "attrs": {}
    })
    add_edge(db, edge_payload)

    write_audit(
        db,
        "task",
        task.task_id,
        "task_created",
        f"type={task_type}, case={case.case_id}"
    )

    return task


def ingest_event_and_create_case(db: Session, payload):
    # 事件进入系统的唯一入口，负责事件入库、案件关联/创建、初始任务决策等核心流程
    event = Event(
        event_id=payload.event_id,
        event_type=payload.event_type,
        source=payload.source,
        source_node_id=payload.source_node_id,
        target_node_id=payload.target_node_id,
        zone=payload.zone,
        confidence=payload.confidence,
        status="new"
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    create_event_node(db, event)

    related_case = find_related_open_case(db, event)

    if related_case:
        event.status = "correlated"
        db.commit()

        edge_payload = type("EdgePayload", (), {
            "edge_id": f"event:{event.event_id}-supports-case:{related_case.case_id}",
            "source_node_id": f"event:{event.event_id}",
            "target_node_id": f"case:{related_case.case_id}",
            "relation_type": "supports",
            "confidence": event.confidence,
            "attrs": {}
        })
        add_edge(db, edge_payload)

        write_audit(
            db,
            "event",
            event.event_id,
            "event_correlated_to_case",
            f"case_id={related_case.case_id}"
        )

        return {
            "status": "correlated",
            "case_id": related_case.case_id
        }

    case_id = f"case-{event.event_id}"

    case = Case(
        case_id=case_id,
        case_type=event.event_type,
        state=CASE_SUSPECTED,
        severity="medium",
        confidence=event.confidence,
        zone=event.zone,
        target_node_id=event.target_node_id,
        source_event_id=event.event_id
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    create_case_node(db, case)

    edge_payload = type("EdgePayload", (), {
        "edge_id": f"event:{event.event_id}-creates-case:{case.case_id}",
        "source_node_id": f"event:{event.event_id}",
        "target_node_id": f"case:{case.case_id}",
        "relation_type": "creates",
        "confidence": event.confidence,
        "attrs": {}
    })
    add_edge(db, edge_payload)

    initial_task = decide_initial_task(db, case)

    write_audit(
        db,
        "case",
        case.case_id,
        "case_created",
        f"type={case.case_type}, initial_task={initial_task.task_id}"
    )

    return {
        "status": "case_created",
        "case_id": case.case_id,
        "initial_task_id": initial_task.task_id
    }


def decide_initial_task(db: Session, case: Case):
    if case.case_type == "illegal_parking_detected":
        case.state = CASE_VERIFYING
        db.commit()

        return create_task(
            db=db,
            case=case,
            task_type="remote_verify",
            priority="high",
            sla_minutes=3,
            fallback_chain="cloud_operator,human"
        )

    if case.case_type == "lane_blocked_detected":
        case.state = CASE_CONFIRMED
        case.severity = "high"
        db.commit()

        return create_task(
            db=db,
            case=case,
            task_type="clear_blocked_lane",
            priority="critical",
            sla_minutes=3,
            fallback_chain="human,robot,cloud_operator"
        )

    return create_task(
        db=db,
        case=case,
        task_type="manual_review",
        priority="medium",
        sla_minutes=15,
        fallback_chain="cloud_operator,human"
    )


def handle_task_outcome(db: Session, payload):
    task = db.query(Task).filter(Task.task_id == payload.task_id).first()
    if not task:
        raise ValueError("Task not found")

    case = db.query(Case).filter(Case.case_id == task.case_id).first()
    if not case:
        raise ValueError("Case not found")

    outcome = TaskOutcome(
        outcome_id=payload.outcome_id,
        task_id=payload.task_id,
        case_id=case.case_id,
        outcome_type=payload.outcome_type,
        confidence=payload.confidence,
        note=payload.note,
        created_by=payload.created_by
    )
    db.add(outcome)

    task.status = "done"
    db.commit()
    db.refresh(outcome)

    if payload.evidence_url:
        evidence_node = SceneNode(
            node_id=f"evidence:{payload.outcome_id}",
            node_type="evidence",
            name="evidence",
            zone=case.zone,
            state="created",
            confidence=payload.confidence,
            attrs={
                "url": payload.evidence_url,
                "note": payload.note
            }
        )
        db.add(evidence_node)
        db.commit()

        edge_payload = type("EdgePayload", (), {
            "edge_id": f"task:{task.task_id}-produces-evidence:{payload.outcome_id}",
            "source_node_id": f"task:{task.task_id}",
            "target_node_id": f"evidence:{payload.outcome_id}",
            "relation_type": "produces",
            "confidence": payload.confidence,
            "attrs": {}
        })
        add_edge(db, edge_payload)

    decision = decision_gateway(db, case, task, outcome)

    write_audit(
        db,
        "case",
        case.case_id,
        "task_outcome_handled",
        f"task={task.task_id}, outcome={payload.outcome_type}, next={decision}"
    )

    return decision


def close_case(db: Session, case: Case, reason: str):
    case.state = CASE_CLOSED
    case.current_task_id = None
    case.updated_at = datetime.utcnow()
    db.commit()

    update_node_state(
        db,
        f"case:{case.case_id}",
        CASE_CLOSED,
        confidence=case.confidence
    )

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
        "reason": reason
    }


def decision_gateway(db: Session, case: Case, task: Task, outcome: TaskOutcome):
    """
    核心状态机,这是最核心的动态决策网关：
    同一个事件，后续任务由任务结果动态决定。
    """

    if task.task_type == "remote_verify":
        if outcome.outcome_type == "false_alarm":
            case.confidence = min(case.confidence, outcome.confidence)
            return close_case(db, case, "remote_verify_false_alarm")

        if outcome.outcome_type == "confirmed_illegal":
            case.state = CASE_CONFIRMED
            case.confidence = max(case.confidence, outcome.confidence)
            db.commit()

            if case.target_node_id:
                update_node_state(
                    db,
                    case.target_node_id,
                    "illegal",
                    confidence=outcome.confidence
                )

            next_task = create_task(
                db=db,
                case=case,
                task_type="capture_evidence",
                priority="high",
                sla_minutes=5,
                fallback_chain="robot,human,cloud_operator"
            )

            return {
                "status": "next_task_created",
                "next_task_id": next_task.task_id,
                "case_state": case.state
            }

        if outcome.outcome_type == "low_confidence":
            case.state = CASE_VERIFYING
            db.commit()

            next_task = create_task(
                db=db,
                case=case,
                task_type="robot_recheck",
                priority="high",
                sla_minutes=8,
                fallback_chain="robot,human"
            )

            return {
                "status": "next_task_created",
                "next_task_id": next_task.task_id,
                "case_state": case.state
            }

        if outcome.outcome_type == "lane_blocking":
            case.state = CASE_ESCALATED
            case.severity = "critical"
            db.commit()

            next_task = create_task(
                db=db,
                case=case,
                task_type="clear_blocked_lane",
                priority="critical",
                sla_minutes=3,
                fallback_chain="human,robot,cloud_operator"
            )

            return {
                "status": "escalated",
                "next_task_id": next_task.task_id,
                "case_state": case.state
            }

    if task.task_type == "robot_recheck":
        if outcome.outcome_type == "cleared":
            if case.target_node_id:
                update_node_state(
                    db,
                    case.target_node_id,
                    "free",
                    confidence=outcome.confidence
                )

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
                "next_task_id": next_task.task_id,
                "case_state": case.state
            }

    if task.task_type == "capture_evidence":
        if outcome.outcome_type == "evidence_captured":
            case.state = CASE_WAITING
            db.commit()

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
                "next_task_id": next_task.task_id,
                "case_state": case.state
            }

    if task.task_type == "notify_property":
        if outcome.outcome_type == "notified":
            return close_case(db, case, "property_notified")

    if task.task_type == "clear_blocked_lane":
        if outcome.outcome_type == "cleared":
            return close_case(db, case, "lane_cleared")

        if outcome.outcome_type == "failed":
            case.state = CASE_ESCALATED
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
                "next_task_id": next_task.task_id,
                "case_state": case.state
            }

    return {
        "status": "no_rule_matched",
        "case_id": case.case_id,
        "case_state": case.state
    }