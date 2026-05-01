from sqlalchemy.orm import Session
from .event_engine import ingest_event
from .task_chain import create_task_chain_for_event
from .audit import write_audit


def process_event(db: Session, payload):
    event, action = ingest_event(db, payload)

    if action == "merged":
        return {
            "event_id": event.event_id,
            "status": "merged",
            "merged_into": event.merged_into
        }

    tasks = create_task_chain_for_event(db, event)

    write_audit(
        db,
        "event",
        event.event_id,
        "event_processed_by_agent",
        f"tasks={len(tasks)}"
    )

    return {
        "event_id": event.event_id,
        "status": "processed",
        "chain_id": f"chain-{event.event_id}",
        "task_count": len(tasks),
        "tasks": [t.task_id for t in tasks]
    }