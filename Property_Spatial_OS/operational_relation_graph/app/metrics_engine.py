from sqlalchemy.orm import Session

from .models import Case, Task, FeedbackRecord, SLAViolation, RiskProfile


def get_operational_metrics(db: Session):
    total_cases = db.query(Case).count()
    open_cases = db.query(Case).filter(Case.state != "closed").count()
    closed_cases = db.query(Case).filter(Case.state == "closed").count()

    total_tasks = db.query(Task).count()
    pending_tasks = db.query(Task).filter(Task.status.in_(["created", "assigned"])).count()
    done_tasks = db.query(Task).filter(Task.status == "done").count()

    false_positive = db.query(FeedbackRecord).filter(
        FeedbackRecord.feedback_type == "false_positive"
    ).count()

    true_positive = db.query(FeedbackRecord).filter(
        FeedbackRecord.feedback_type == "true_positive"
    ).count()

    sla_violations = db.query(SLAViolation).count()

    closure_rate = closed_cases / total_cases if total_cases else 0
    task_done_rate = done_tasks / total_tasks if total_tasks else 0

    return {
        "total_cases": total_cases,
        "open_cases": open_cases,
        "closed_cases": closed_cases,
        "case_closure_rate": round(closure_rate, 2),
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "done_tasks": done_tasks,
        "task_done_rate": round(task_done_rate, 2),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "sla_violations": sla_violations
    }


def get_top_risk_nodes(db: Session, limit: int = 10):
    return db.query(RiskProfile).order_by(
        RiskProfile.risk_score.desc()
    ).limit(limit).all()
