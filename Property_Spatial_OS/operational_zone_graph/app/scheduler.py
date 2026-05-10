from sqlalchemy.orm import Session

from .models import Task, Executor, FunctionalZone
from .zone_graph import get_adjacent_zone_ids, update_zone_state
from .audit import write_audit
from .constants import (
    TASK_CREATED,
    TASK_ASSIGNED,
    EXECUTOR_IDLE,
    EXECUTOR_BUSY,
    PRIORITY_SCORE
)


def parse_chain(chain: str):
    return [x.strip() for x in chain.split(",") if x.strip()]


def executor_can_handle(executor: Executor, task_type: str):
    supported = [x.strip() for x in executor.can_handle.split(",") if x.strip()]
    return task_type in supported


def get_zone_heat(db: Session, zone_id: str):
    zone = db.query(FunctionalZone).filter(
        FunctionalZone.zone_id == zone_id
    ).first()

    return zone.heat if zone else 1


def task_score(db: Session, task: Task):
    priority_score = PRIORITY_SCORE.get(task.priority, 0)
    sla_score = max(0, 60 - task.sla_minutes)
    zone_score = get_zone_heat(db, task.zone_id) * 5
    return priority_score + sla_score + zone_score


def find_executor_in_zone(db: Session, task: Task, zone_id: str):
    for executor_type in parse_chain(task.fallback_chain):
        candidates = db.query(Executor).filter(
            Executor.zone_id == zone_id,
            Executor.executor_type == executor_type,
            Executor.status == EXECUTOR_IDLE,
            Executor.online == True
        ).all()

        for executor in candidates:
            if executor_can_handle(executor, task.task_type):
                return executor

    return None


def find_executor(db: Session, task: Task):
    executor = find_executor_in_zone(db, task, task.zone_id)
    if executor:
        return executor, "same_zone"

    for adjacent_zone_id in get_adjacent_zone_ids(db, task.zone_id):
        executor = find_executor_in_zone(db, task, adjacent_zone_id)
        if executor:
            return executor, f"adjacent_zone:{adjacent_zone_id}"

    return None, "no_executor"


def run_scheduler(db: Session):
    tasks = db.query(Task).filter(
        Task.status == TASK_CREATED
    ).all()

    tasks = sorted(tasks, key=lambda t: task_score(db, t), reverse=True)

    results = []

    for task in tasks:
        executor, reason = find_executor(db, task)

        if not executor:
            results.append({
                "task_id": task.task_id,
                "status": "waiting_no_executor",
                "reason": reason
            })
            continue

        task.status = TASK_ASSIGNED
        task.assigned_executor_id = executor.executor_id

        executor.status = EXECUTOR_BUSY
        executor.current_task_id = task.task_id

        db.commit()

        update_zone_state(db, task.zone_id)

        write_audit(
            db,
            "task",
            task.task_id,
            "task_assigned",
            f"executor={executor.executor_id}, reason={reason}"
        )

        results.append({
            "task_id": task.task_id,
            "assigned_to": executor.executor_id,
            "executor_zone": executor.zone_id,
            "reason": reason,
            "status": "assigned"
        })

    return results