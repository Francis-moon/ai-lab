from datetime import datetime
from sqlalchemy.orm import Session

from .models import FeedbackRecord, RiskProfile, Case
from .audit import write_audit
from .map_patch import propose_map_patch


def get_or_create_risk_profile(db: Session, case: Case):
    profile_id = f"risk-{case.target_node_id or case.zone}"

    profile = db.query(RiskProfile).filter(
        RiskProfile.profile_id == profile_id
    ).first()

    if profile:
        return profile

    profile = RiskProfile(
        profile_id=profile_id,
        target_node_id=case.target_node_id or "zone:" + case.zone,
        zone=case.zone,
        risk_score=0.0
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile


def update_risk_profile(db: Session, profile: RiskProfile, feedback_type: str):
    if feedback_type == "true_positive":
        profile.true_positive_count += 1
        profile.risk_score += 5

    elif feedback_type == "false_positive":
        profile.false_positive_count += 1
        profile.risk_score = max(0, profile.risk_score - 3)

    elif feedback_type == "duplicate":
        profile.duplicate_count += 1

    elif feedback_type == "map_error":
        profile.risk_score += 2

    elif feedback_type == "camera_blindspot":
        profile.risk_score += 4

    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)

    return profile


def submit_feedback(db: Session, payload):
    case = db.query(Case).filter(Case.case_id == payload.case_id).first()

    if not case:
        raise ValueError("Case not found")

    feedback = FeedbackRecord(
        feedback_id=payload.feedback_id,
        case_id=payload.case_id,
        task_id=payload.task_id,
        feedback_type=payload.feedback_type,
        root_cause=payload.root_cause,
        note=payload.note,
        created_by=payload.created_by,
        attrs=payload.attrs
    )

    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    profile = get_or_create_risk_profile(db, case)
    update_risk_profile(db, profile, payload.feedback_type)

    if payload.feedback_type in ["map_error", "camera_blindspot"]:
        propose_map_patch(
            db=db,
            target_node_id=case.target_node_id or f"zone:{case.zone}",
            patch_type="mark_blindspot" if payload.feedback_type == "camera_blindspot" else "update_attrs",
            source_case_id=case.case_id,
            payload={
                "feedback_type": payload.feedback_type,
                "root_cause": payload.root_cause,
                "note": payload.note
            }
        )

    write_audit(
        db,
        "case",
        case.case_id,
        "feedback_submitted",
        f"type={payload.feedback_type}, root_cause={payload.root_cause}"
    )

    return {
        "feedback_id": feedback.feedback_id,
        "case_id": case.case_id,
        "risk_profile": profile.profile_id,
        "risk_score": profile.risk_score
    }