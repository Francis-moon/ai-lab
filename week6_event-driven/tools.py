def inspect_slot(slot_id: str) -> str:
    return f"{slot_id} 已完成巡检"


def capture_evidence(slot_id: str) -> str:
    return f"{slot_id} 已采集现场证据"


def notify_security(slot_id: str) -> str:
    return f"{slot_id} 已通知安保人员"


def recheck_slot(slot_id: str) -> str:
    return f"{slot_id} 已完成复核，无持续异常"
