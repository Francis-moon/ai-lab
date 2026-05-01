from sqlalchemy.orm import Session

from .models import Task, Executor
from .audit import write_audit
from .constants import TASK_CREATED, TASK_ASSIGNED, EXECUTOR_IDLE, EXECUTOR_BUSY


PRIORITY_SCORE = {
    "critical": 100,
    "high": 70,
    "medium": 40,
    "low": 10
}


def parse_chain(chain: str):
    return [x.strip() for x in chain.split(",") if x.strip()]


def executor_can_handle(executor: Executor, task_type: str):
    return task_type in [x.strip() for x in executor.can_handle.split(",")]


def task_score(task: Task):
    return PRIORITY_SCORE.get(task.priority, 0) + max(0, 60 - task.sla_minutes)


def find_executor(db: Session, task: Task):
    for executor_type in parse_chain(task.fallback_chain):
        candidates = db.query(Executor).filter(
            Executor.executor_type == executor_type,
            Executor.zone == task.zone,
            Executor.status == EXECUTOR_IDLE,
            Executor.online == True
        ).all()

        for e in candidates:
            if executor_can_handle(e, task.task_type):
                return e

    return None


def run_scheduler(db: Session):
    tasks = db.query(Task).filter(Task.status == TASK_CREATED).all()
    tasks = sorted(tasks, key=task_score, reverse=True)

    results = []

    for task in tasks:
        executor = find_executor(db, task)

        if not executor:
            results.append({
                "task_id": task.task_id,
                "status": "waiting_no_executor"
            })
            continue

        task.status = TASK_ASSIGNED
        task.assigned_executor_id = executor.executor_id

        executor.status = EXECUTOR_BUSY
        executor.current_task_id = task.task_id

        db.commit()

        write_audit(
            db,
            "task",
            task.task_id,
            "task_assigned",
            f"executor={executor.executor_id}"
        )

        results.append({
            "task_id": task.task_id,
            "assigned_to": executor.executor_id,
            "status": "assigned"
        })

    return results