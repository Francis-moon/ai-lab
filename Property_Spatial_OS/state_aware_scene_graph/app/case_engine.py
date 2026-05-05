# 这是核心：不是固定任务链，而是结果驱动的动态状态机
# Event 创建关系假设；Outcome 更新关系边。
from datetime import datetime
from sqlalchemy.orm import Session

from .models import Event, Case, Task, TaskOutcome, SceneNode
from .constants import CASE_SUSPECTED, CASE_VERIFYING, CASE_CONFIRMED, CASE_CLOSED
from .audit import write_audit
from .relation_engine import (
    upsert_relation_hypothesis,
    strengthen_relation,
    weaken_relation,
    confirm_relation,
    reject_relation,
    create_or_update_node_state,
)


def create_scene_node_if_missing(db: Session, node_id: str, node_type: str, name: str, zone: str, state: str = None):
    node = db.query(SceneNode).filter(SceneNode.node_id == node_id).first()
    if node:
        return node

    node = SceneNode(
        node_id=node_id,
        node_type=node_type,
        name=name,
        zone=zone,
        state=state,
        confidence=80,
        attrs={},
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def create_task(db: Session, case: Case, task_type: str, priority: str, sla_minutes: int, fallback_chain: str):
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
        status="created",
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    create_scene_node_if_missing(
        db,
        node_id=f"task:{task.task_id}",
        node_type="task",
        name=task.task_type,
        zone=task.zone,
        state=task.status,
    )

    confirm_relation(
        db,
        source_node_id=f"case:{case.case_id}",
        relation_type="requires",
        target_node_id=f"task:{task.task_id}",
        source_type="system",
        source_id=case.case_id,
        created_by="system",
        confidence=95,
        detail="case requires task",
    )

    case.current_task_id = task.task_id
    db.commit()

    return task


def ingest_event(db: Session, payload):
    event = Event(
        event_id=payload.event_id,
        event_type=payload.event_type,
        source=payload.source,
        source_node_id=payload.source_node_id,
        target_node_id=payload.target_node_id,
        zone=payload.zone,
        confidence=payload.confidence,
        status="new",
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    create_scene_node_if_missing(
        db,
        node_id=f"event:{event.event_id}",
        node_type="event",
        name=event.event_type,
        zone=event.zone,
        state="new",
    )

    if event.source_node_id:
        upsert_relation_hypothesis(
            db,
            source_node_id=event.source_node_id,
            relation_type="detected",
            target_node_id=f"event:{event.event_id}",
            confidence=event.confidence,
            created_by=event.source,
            source_type="event",
            source_id=event.event_id,
            detail="event detected by source node",
        )

    if event.target_node_id:
        upsert_relation_hypothesis(
            db,
            source_node_id=f"event:{event.event_id}",
            relation_type="observed_on",
            target_node_id=event.target_node_id,
            confidence=event.confidence,
            created_by=event.source,
            source_type="event",
            source_id=event.event_id,
            detail="event observed on target node",
        )

        if event.source_node_id:
            strengthen_relation(
                db,
                source_node_id=event.source_node_id,
                relation_type="observes",
                target_node_id=event.target_node_id,
                delta=5,
                source_type="event",
                source_id=event.event_id,
                created_by=event.source,
                detail="source produced event on target",
            )

    case_id = f"case-{event.event_id}"

    case = Case(
        case_id=case_id,
        case_type=event.event_type,
        state=CASE_SUSPECTED,
        confidence=event.confidence,
        zone=event.zone,
        target_node_id=event.target_node_id,
        source_event_id=event.event_id,
    )

    db.add(case)
    db.commit()
    db.refresh(case)

    create_scene_node_if_missing(
        db,
        node_id=f"case:{case.case_id}",
        node_type="case",
        name=case.case_type,
        zone=case.zone,
        state=case.state,
    )

    upsert_relation_hypothesis(
        db,
        source_node_id=f"event:{event.event_id}",
        relation_type="supports",
        target_node_id=f"case:{case.case_id}",
        confidence=event.confidence,
        created_by=event.source,
        source_type="event",
        source_id=event.event_id,
        detail="event may support case",
    )

    initial_task = create_task(
        db,
        case,
        task_type="remote_verify",
        priority="high",
        sla_minutes=3,
        fallback_chain="cloud_operator,human",
    )

    case.state = CASE_VERIFYING
    db.commit()

    write_audit(
        db,
        "case",
        case.case_id,
        "case_created",
        f"initial_task={initial_task.task_id}",
    )

    return {
        "status": "case_created",
        "case_id": case.case_id,
        "initial_task_id": initial_task.task_id,
    }


def handle_task_outcome(db: Session, payload):
    task = db.query(Task).filter(Task.task_id == payload.task_id).first()
    if not task:
        raise ValueError("Task not found")

    case = db.query(Case).filter(Case.case_id == task.case_id).first()
    if not case:
        raise ValueError("Case not found")

    outcome = TaskOutcome(
        outcome_id=payload.outcome_id,
        task_id=task.task_id,
        case_id=case.case_id,
        outcome_type=payload.outcome_type,
        confidence=payload.confidence,
        evidence_node_id=None,
        note=payload.note,
        created_by=payload.created_by,
    )

    db.add(outcome)

    task.status = "done"
    db.commit()
    db.refresh(outcome)

    # 1. 远程确认：误报
    if task.task_type == "remote_verify" and outcome.outcome_type == "false_alarm":
        case.state = CASE_CLOSED
        case.confidence = min(case.confidence, outcome.confidence)
        case.current_task_id = None

        reject_relation(
            db,
            source_node_id=f"event:{case.source_event_id}",
            relation_type="supports",
            target_node_id=f"case:{case.case_id}",
            source_type="task_outcome",
            source_id=outcome.outcome_id,
            created_by=outcome.created_by,
            detail="remote verify says false alarm",
        )

        if case.target_node_id:
            create_or_update_node_state(db, case.target_node_id, "normal", outcome.confidence)

        db.commit()

        return {
            "status": "case_closed",
            "case_id": case.case_id,
            "reason": "false_alarm",
        }

    # 2. 远程确认：低置信度，需要机器人复核
    if task.task_type == "remote_verify" and outcome.outcome_type == "low_confidence":
        case.state = CASE_VERIFYING
        db.commit()

        next_task = create_task(
            db,
            case,
            task_type="robot_recheck",
            priority="high",
            sla_minutes=8,
            fallback_chain="robot,human",
        )

        strengthen_relation(
            db,
            source_node_id=f"event:{case.source_event_id}",
            relation_type="supports",
            target_node_id=f"case:{case.case_id}",
            delta=5,
            source_type="task_outcome",
            source_id=outcome.outcome_id,
            created_by=outcome.created_by,
            detail="low confidence, still needs recheck",
        )

        return {
            "status": "next_task_created",
            "next_task_id": next_task.task_id,
            "case_state": case.state,
        }

    # 3. 远程确认：确认违停
    if task.task_type == "remote_verify" and outcome.outcome_type == "confirmed_illegal":
        case.state = CASE_CONFIRMED
        case.confidence = max(case.confidence, outcome.confidence)
        db.commit()

        confirm_relation(
            db,
            source_node_id=f"event:{case.source_event_id}",
            relation_type="supports",
            target_node_id=f"case:{case.case_id}",
            source_type="task_outcome",
            source_id=outcome.outcome_id,
            created_by=outcome.created_by,
            confidence=outcome.confidence,
            detail="remote operator confirmed illegal parking",
        )

        if case.target_node_id:
            create_or_update_node_state(db, case.target_node_id, "suspected_illegal", outcome.confidence)

        next_task = create_task(
            db,
            case,
            task_type="capture_evidence",
            priority="high",
            sla_minutes=5,
            fallback_chain="robot,human,cloud_operator",
        )

        return {
            "status": "next_task_created",
            "next_task_id": next_task.task_id,
            "case_state": case.state,
        }

    # 4. 机器人复核：仍然存在
    if task.task_type == "robot_recheck" and outcome.outcome_type == "still_present":
        case.state = CASE_CONFIRMED
        case.confidence = max(case.confidence, outcome.confidence)
        db.commit()

        vehicle_node_id = f"vehicle:unknown-{case.case_id}"
        create_scene_node_if_missing(
            db,
            node_id=vehicle_node_id,
            node_type="vehicle",
            name="unknown vehicle",
            zone=case.zone,
            state="present",
        )

        if case.target_node_id:
            confirm_relation(
                db,
                source_node_id=vehicle_node_id,
                relation_type="occupies",
                target_node_id=case.target_node_id,
                source_type="task_outcome",
                source_id=outcome.outcome_id,
                created_by=outcome.created_by,
                confidence=outcome.confidence,
                detail="robot verified vehicle still present",
            )

            create_or_update_node_state(db, case.target_node_id, "confirmed_illegal", outcome.confidence)

        confirm_relation(
            db,
            source_node_id=outcome.created_by,
            relation_type="verified",
            target_node_id=f"case:{case.case_id}",
            source_type="task_outcome",
            source_id=outcome.outcome_id,
            created_by=outcome.created_by,
            confidence=outcome.confidence,
            detail="robot verified case",
        )

        next_task = create_task(
            db,
            case,
            task_type="capture_evidence",
            priority="high",
            sla_minutes=5,
            fallback_chain="robot,human",
        )

        return {
            "status": "next_task_created",
            "next_task_id": next_task.task_id,
            "case_state": case.state,
        }

    # 5. 机器人复核：已消失
    if task.task_type == "robot_recheck" and outcome.outcome_type == "cleared":
        case.state = CASE_CLOSED
        case.current_task_id = None

        if case.target_node_id:
            create_or_update_node_state(db, case.target_node_id, "normal", outcome.confidence)

        reject_relation(
            db,
            source_node_id=f"event:{case.source_event_id}",
            relation_type="supports",
            target_node_id=f"case:{case.case_id}",
            source_type="task_outcome",
            source_id=outcome.outcome_id,
            created_by=outcome.created_by,
            detail="robot recheck cleared",
        )

        db.commit()

        return {
            "status": "case_closed",
            "case_id": case.case_id,
            "reason": "robot_recheck_cleared",
        }

    return {
        "status": "no_rule_matched",
        "case_id": case.case_id,
        "task_type": task.task_type,
        "outcome": outcome.outcome_type,
    }