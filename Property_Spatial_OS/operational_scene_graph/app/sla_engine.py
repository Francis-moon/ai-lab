from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .models import Task, Case, Executor, SLAViolation
from .audit import write_audit


def create_violation(db: Session, task: Task, violation_type: str, severity: str, action_taken: str):
    violation = SLAViolation(
        violation_id=f"sla-{task.task_id}-{int(datetime.utcnow().timestamp())}",
        task_id=task.task_id,
        case_id=task.case_id,
        violation_type=violation_type,
        severity=severity,
        action_taken=action_taken
    )

    db.add(violation)
    db.commit()

    write_audit(
        db,
        "task",
        task.task_id,
        "sla_violation",
        f"type={violation_type}, severity={severity}, action={action_taken}"
    )

    return violation


def check_task_sla(db: Session):
    now = datetime.utcnow()

    tasks = db.query(Task).filter(
        Task.status.in_(["created", "assigned"])
    ).all()

    results = []

    for task in tasks:
        deadline = task.created_at + timedelta(minutes=task.sla_minutes)

        if now <= deadline:
            continue

        case = db.query(Case).filter(Case.case_id == task.case_id).first()

        if task.status == "created":
            violation_type = "not_assigned_timeout"
            action = "increase_priority_and_escalate"
            task.priority = "critical"
            task.fallback_chain = "human,cloud_operator,robot"

            if case:
                case.state = "escalated"
                case.severity = "critical"

            create_violation(db, task, violation_type, "high", action)

            results.append({
                "task_id": task.task_id,
                "violation": violation_type,
                "action": action
            })

        elif task.status == "assigned":
            executor = None
            if task.assigned_executor_id:
                executor = db.query(Executor).filter(
                    Executor.executor_id == task.assigned_executor_id
                ).first()

            violation_type = "not_completed_timeout"
            action = "release_executor_and_requeue"

            if executor:
                executor.status = "idle"
                executor.current_task_id = None

            task.status = "created"
            task.assigned_executor_id = None
            task.priority = "critical"
            task.fallback_chain = "human,cloud_operator,robot"

            if case:
                case.state = "escalated"
                case.severity = "critical"

            create_violation(db, task, violation_type, "critical", action)

            results.append({
                "task_id": task.task_id,
                "violation": violation_type,
                "action": action
            })

    db.commit()
    return results
