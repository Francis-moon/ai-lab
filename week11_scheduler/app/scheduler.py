# 核心部分
from sqlalchemy.orm import Session
from .models import Task, Executor
from .constants import (
    TASK_STATUS_CREATED,
    TASK_STATUS_ASSIGNED,
    TASK_STATUS_DONE,
    TASK_STATUS_FAILED,
    EXECUTOR_STATUS_IDLE,
    EXECUTOR_STATUS_BUSY,
    EXECUTOR_STATUS_CHARGING,
    ROBOT_BATTERY_LOW_THRESHOLD,
)


PRIORITY_SCORE = {
    "critical": 100,
    "high": 70,
    "medium": 40,
    "low": 10,
}


def parse_fallback_chain(chain: str):
    return [x.strip() for x in chain.split(",") if x.strip()]


def executor_can_handle(executor: Executor, task_type: str):
    supported = [x.strip() for x in executor.can_handle.split(",") if x.strip()]
    return task_type in supported


def get_available_executors(db: Session, zone: str, executor_type: str, task_type: str):
    candidates = db.query(Executor).filter(
        Executor.zone == zone,
        Executor.executor_type == executor_type,
        Executor.online == True
    ).all()

    result = []
    for e in candidates:
        if e.status != EXECUTOR_STATUS_IDLE:
            continue
        if not executor_can_handle(e, task_type):
            continue
        if e.executor_type == "robot" and (e.battery_level is None or e.battery_level < ROBOT_BATTERY_LOW_THRESHOLD):
            continue
        result.append(e)
    return result


def task_score(task: Task):
    priority_score = PRIORITY_SCORE.get(task.priority, 0)
    heat_score = task.zone_heat * 5
    sla_score = max(0, 60 - task.sla_minutes)  # SLA 越短越高优
    return priority_score + heat_score + sla_score


def sort_tasks(tasks):
    return sorted(tasks, key=task_score, reverse=True)


def ensure_robot_charging_task(db: Session, robot: Executor):
    if robot.executor_type != "robot":
        return None

    if robot.battery_level is None or robot.battery_level >= ROBOT_BATTERY_LOW_THRESHOLD:
        return None

    existing = db.query(Task).filter(
        Task.task_type == "charge_robot",
        Task.assigned_executor_id == robot.executor_id,
        Task.status.in_(["created", "assigned", "in_progress"])
    ).first()
    if existing:
        return existing

    task = Task(
        task_id=f"charge-{robot.executor_id}",
        task_type="charge_robot",
        slot_id=None,
        zone=robot.zone,
        preferred_assignee="robot",
        assigned_executor_id=None,
        priority="critical",
        sla_minutes=1,
        zone_heat=1,
        fallback_chain="robot",
        status="created"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def assign_task_to_executor(db: Session, task: Task, executor: Executor):
    task.assigned_executor_id = executor.executor_id
    task.status = TASK_STATUS_ASSIGNED

    executor.status = EXECUTOR_STATUS_CHARGING if task.task_type == "charge_robot" else EXECUTOR_STATUS_BUSY
    executor.current_task_id = task.task_id

    db.commit()
    db.refresh(task)
    db.refresh(executor)
    return task, executor


def schedule_pending_tasks(db: Session):
    # 先扫描低电量机器人，自动生成充电任务
    robots = db.query(Executor).filter(Executor.executor_type == "robot", Executor.online == True).all()
    for robot in robots:
        ensure_robot_charging_task(db, robot)

    pending_tasks = db.query(Task).filter(Task.status == TASK_STATUS_CREATED).all()
    pending_tasks = sort_tasks(pending_tasks)

    scheduling_results = []

    for task in pending_tasks:
        chain = parse_fallback_chain(task.fallback_chain)
        assigned = False

        for executor_type in chain:
            candidates = get_available_executors(db, task.zone, executor_type, task.task_type)

            # 简单策略：同区优先，选第一个
            if candidates:
                executor = candidates[0]
                assign_task_to_executor(db, task, executor)
                scheduling_results.append({
                    "task_id": task.task_id,
                    "assigned_to": executor.executor_id,
                    "executor_type": executor.executor_type,
                    "status": "assigned"
                })
                assigned = True
                break

        if not assigned:
            scheduling_results.append({
                "task_id": task.task_id,
                "assigned_to": None,
                "status": "waiting_no_executor"
            })

    return scheduling_results


def complete_task(db: Session, task_id: str):
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise ValueError("Task not found")

    executor = None
    if task.assigned_executor_id:
        executor = db.query(Executor).filter(Executor.executor_id == task.assigned_executor_id).first()

    task.status = TASK_STATUS_DONE

    if executor:
        # 任务完成自动释放执行体
        executor.current_task_id = None
        if executor.executor_type == "robot":
            if task.task_type == "charge_robot":
                executor.battery_level = 100
            else:
                executor.battery_level = max(0, (executor.battery_level or 100) - 10)
            executor.status = EXECUTOR_STATUS_IDLE
        else:
            executor.status = EXECUTOR_STATUS_IDLE

    db.commit()
    return {
        "task_id": task.task_id,
        "task_status": task.status,
        "released_executor": executor.executor_id if executor else None,
        "executor_status": executor.status if executor else None,
        "battery_level": executor.battery_level if executor and executor.executor_type == "robot" else None
    }


def fail_task_with_fallback(db: Session, task_id: str):
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise ValueError("Task not found")

    old_executor = None
    if task.assigned_executor_id:
        old_executor = db.query(Executor).filter(Executor.executor_id == task.assigned_executor_id).first()
        if old_executor:
            old_executor.current_task_id = None
            old_executor.status = EXECUTOR_STATUS_IDLE

    task.status = TASK_STATUS_CREATED
    task.assigned_executor_id = None

    db.commit()

    # 重新调度，走 fallback 链
    results = schedule_pending_tasks(db)
    return {
        "task_id": task.task_id,
        "status": "requeued",
        "old_executor": old_executor.executor_id if old_executor else None,
        "reschedule_results": results
    }