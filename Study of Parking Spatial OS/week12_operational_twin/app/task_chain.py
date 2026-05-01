from sqlalchemy.orm import Session
from .models import Task, ZoneState
from .audit import write_audit


def get_zone_heat(db: Session, zone: str):
    z = db.query(ZoneState).filter(ZoneState.zone == zone).first()
    return z.heat if z else 1


def create_task_chain_for_event(db: Session, event):
    zone_heat = get_zone_heat(db, event.zone)
    chain_id = f"chain-{event.event_id}"

    tasks = []

    if event.event_type == "illegal_parking_detected":
        tasks = [
            Task(
                task_id=f"{event.event_id}-01-remote-verify",
                task_type="remote_verify",
                slot_id=event.slot_id,
                zone=event.zone,
                priority="high" if zone_heat >= 7 else "medium",
                sla_minutes=3,
                zone_heat=zone_heat,
                fallback_chain="cloud_operator,human",
                chain_id=chain_id,
                step_order=1
            ),
            Task(
                task_id=f"{event.event_id}-02-robot-recheck",
                task_type="recheck_slot",
                slot_id=event.slot_id,
                zone=event.zone,
                priority="high",
                sla_minutes=8,
                zone_heat=zone_heat,
                fallback_chain="robot,human",
                chain_id=chain_id,
                step_order=2,
                depends_on_task_id=f"{event.event_id}-01-remote-verify"
            ),
            Task(
                task_id=f"{event.event_id}-03-close-evidence",
                task_type="capture_evidence",
                slot_id=event.slot_id,
                zone=event.zone,
                priority="medium",
                sla_minutes=15,
                zone_heat=zone_heat,
                fallback_chain="robot,human,cloud_operator",
                chain_id=chain_id,
                step_order=3,
                depends_on_task_id=f"{event.event_id}-02-robot-recheck"
            )
        ]

    elif event.event_type == "lane_blocked_detected":
        tasks = [
            Task(
                task_id=f"{event.event_id}-01-clear-lane",
                task_type="clear_blocked_lane",
                slot_id=event.slot_id,
                zone=event.zone,
                priority="critical",
                sla_minutes=3,
                zone_heat=zone_heat,
                fallback_chain="human,robot,cloud_operator",
                chain_id=chain_id,
                step_order=1
            ),
            Task(
                task_id=f"{event.event_id}-02-verify-clear",
                task_type="verify_clearance",
                slot_id=event.slot_id,
                zone=event.zone,
                priority="high",
                sla_minutes=8,
                zone_heat=zone_heat,
                fallback_chain="robot,cloud_operator",
                chain_id=chain_id,
                step_order=2,
                depends_on_task_id=f"{event.event_id}-01-clear-lane"
            )
        ]

    else:
        tasks = [
            Task(
                task_id=f"{event.event_id}-01-review",
                task_type="manual_review",
                slot_id=event.slot_id,
                zone=event.zone,
                priority="low",
                sla_minutes=30,
                zone_heat=zone_heat,
                fallback_chain="cloud_operator,human",
                chain_id=chain_id,
                step_order=1
            )
        ]

    for task in tasks:
        existing = db.query(Task).filter(Task.task_id == task.task_id).first()
        if not existing:
            db.add(task)

    db.commit()

    write_audit(
        db,
        "event",
        event.event_id,
        "task_chain_created",
        f"chain_id={chain_id}, task_count={len(tasks)}"
    )

    return tasks