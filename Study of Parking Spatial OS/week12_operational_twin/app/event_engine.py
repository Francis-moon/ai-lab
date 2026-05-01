from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .models import Event, ZoneState
from .constants import EVENT_NEW, EVENT_MERGED
from .audit import write_audit


DEDUP_WINDOW_MINUTES = 5


def find_duplicate_event(db: Session, event_type: str, slot_id: str, zone: str):
    since = datetime.utcnow() - timedelta(minutes=DEDUP_WINDOW_MINUTES)

    return db.query(Event).filter(
        Event.event_type == event_type,
        Event.slot_id == slot_id,
        Event.zone == zone,
        Event.status == EVENT_NEW,
        Event.created_at >= since
    ).first()


def update_zone_state(db: Session, zone: str):
    z = db.query(ZoneState).filter(ZoneState.zone == zone).first()
    if not z:
        z = ZoneState(zone=zone, heat=1, status="normal", active_event_count=0)
        db.add(z)
        db.commit()
        db.refresh(z)

    active_count = db.query(Event).filter(
        Event.zone == zone,
        Event.status == EVENT_NEW
    ).count()

    z.active_event_count = active_count
    z.heat = min(10, 1 + active_count * 2)

    if active_count == 0:
        z.status = "normal"
    elif active_count <= 1:
        z.status = "warning"
    elif active_count <= 3:
        z.status = "high_risk"
    else:
        z.status = "blocked"

    db.commit()
    db.refresh(z)

    write_audit(
        db,
        "zone",
        zone,
        "zone_state_updated",
        f"status={z.status}, heat={z.heat}, active_events={active_count}"
    )

    return z


def ingest_event(db: Session, payload):
    duplicate = find_duplicate_event(
        db=db,
        event_type=payload.event_type,
        slot_id=payload.slot_id,
        zone=payload.zone
    )

    if duplicate:
        event = Event(
            event_id=payload.event_id,
            event_type=payload.event_type,
            slot_id=payload.slot_id,
            zone=payload.zone,
            source=payload.source,
            status=EVENT_MERGED,
            merged_into=duplicate.event_id
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        write_audit(
            db,
            "event",
            event.event_id,
            "event_merged",
            f"merged_into={duplicate.event_id}"
        )

        return event, "merged"

    event = Event(
        event_id=payload.event_id,
        event_type=payload.event_type,
        slot_id=payload.slot_id,
        zone=payload.zone,
        source=payload.source,
        status=EVENT_NEW
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    write_audit(
        db,
        "event",
        event.event_id,
        "event_created",
        f"type={event.event_type}, zone={event.zone}, source={event.source}"
    )

    update_zone_state(db, payload.zone)

    return event, "created"