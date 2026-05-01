from sqlalchemy.orm import Session
from .models import Task, Executor
from .constants import (
    TASK_CREATED,
    TASK_ASSIGNED,
    TASK_DONE,
    EXECUTOR_IDLE,
    EXECUTOR_BUSY,
    EXECUTOR_CHARGING,
    ROBOT_LOW_BATTERY
)
from .audit import write_audit


PRIORITY_SCORE = {
    "critical": 100,
    "high": 70,
    "medium": 40,
    "low": 10
}


def parse_chain(chain: str):
    return [x.strip() for x in chain.split(",") if x.strip()]


def can_handle(executor: Executor, task_type: str):
    return task_type in [x.strip() for x in executor.can_handle.split(",")]


def task_dependency_done(db: Session, task: Task):
    if not task.depends_on_task_id:
        return True

    parent = db.query(Task).filter(
        Task.task_id == task.depends_on_task_id
    ).first()

    return parent and parent.status == TASK_DONE


def task_score(task: Task):
    priority = PRIORITY_SCORE.get(task.priority, 0)
    heat = task.zone_heat * 5
    sla = max(0, 60 - task.sla_minutes)
    return priority + heat + sla


def ensure_charging_tasks(db: Session):
    robots = db.query(Executor).filter(
        Executor.executor_type == "robot",
        Executor.online == True
    ).all()

    for robot in robots:
        if robot.battery_level is not None and robot.battery_level < ROBOT_LOW_BATTERY:
            existing = db.query(Task).filter(
                Task.task_id == f"charge-{robot.executor_id}",
                Task.status.in_([TASK_CREATED, TASK_ASSIGNED])
            ).first()

            if not existing:
                task = Task(
                    task_id=f"charge-{robot.executor_id}",
                    task_type="charge_robot",
                    zone=robot.zone,
                    priority="critical",
                    sla_minutes=1,
                    zone_heat=1,
                    fallback_chain="robot"
                )
                db.add(task)
                db.commit()

                write_audit(
                    db,
                    "executor",
                    robot.executor_id,
                    "charging_task_created",
                    f"battery={robot.battery_level}"
                )


def find_executor(db: Session, task: Task):
    for executor_type in parse_chain(task.fallback_chain):
        candidates = db.query(Executor).filter(
            Executor.zone == task.zone,
            Executor.executor_type == executor_type,
            Executor.status == EXECUTOR_IDLE,
            Executor.online == True
        ).all()

        for e in candidates:
            if not can_handle(e, task.task_type):
                continue

            if e.executor_type == "robot":
                if e.battery_level is None:
                    continue
                if e.battery_level < ROBOT_LOW_BATTERY and task.task_type != "charge_robot":
                    continue

            return e

    return None


def run_scheduler(db: Session):
    ensure_charging_tasks(db)

    tasks = db.query(Task).filter(Task.status == TASK_CREATED).all()
    tasks = [t for t in tasks if task_dependency_done(db, t)]
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

        task.assigned_executor_id = executor.executor_id
        task.status = TASK_ASSIGNED

        executor.current_task_id = task.task_id
        executor.status = EXECUTOR_CHARGING if task.task_type == "charge_robot" else EXECUTOR_BUSY

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


def complete_task(db: Session, task_id: str):
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise ValueError("Task not found")

    executor = None
    if task.assigned_executor_id:
        executor = db.query(Executor).filter(
            Executor.executor_id == task.assigned_executor_id
        ).first()

    task.status = TASK_DONE

    if executor:
        executor.current_task_id = None
        executor.status = EXECUTOR_IDLE

        if executor.executor_type == "robot":
            if task.task_type == "charge_robot":
                executor.battery_level = 100
            else:
                executor.battery_level = max(0, executor.battery_level - 10)

    db.commit()

    write_audit(
        db,
        "task",
        task.task_id,
        "task_completed",
        f"executor={task.assigned_executor_id}"
    )

    return {
        "task_id": task.task_id,
        "status": "done",
        "released_executor": task.assigned_executor_id
    }


def fail_task(db: Session, task_id: str):
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise ValueError("Task not found")

    old_executor_id = task.assigned_executor_id

    if old_executor_id:
        executor = db.query(Executor).filter(
            Executor.executor_id == old_executor_id
        ).first()
        if executor:
            executor.status = EXECUTOR_IDLE
            executor.current_task_id = None

    task.status = TASK_CREATED
    task.assigned_executor_id = None
    db.commit()

    write_audit(
        db,
        "task",
        task.task_id,
        "task_failed_requeued",
        f"old_executor={old_executor_id}"
    )

    return {
        "task_id": task.task_id,
        "status": "requeued"
    }