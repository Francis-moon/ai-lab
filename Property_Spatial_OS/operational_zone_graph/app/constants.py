CASE_SUSPECTED = "suspected"
CASE_VERIFYING = "verifying"
CASE_CONFIRMED = "confirmed"
CASE_ESCALATED = "escalated"
CASE_CLOSED = "closed"

TASK_CREATED = "created"
TASK_ASSIGNED = "assigned"
TASK_DONE = "done"
TASK_FAILED = "failed"

EXECUTOR_IDLE = "idle"
EXECUTOR_BUSY = "busy"
EXECUTOR_OFFLINE = "offline"

ZONE_NORMAL = "normal"
ZONE_WARNING = "warning"
ZONE_HIGH_RISK = "high_risk"
ZONE_BLOCKED = "blocked"
ZONE_DEVICE_FAULT = "device_fault"

EDGE_HYPOTHESIS = "hypothesis"
EDGE_CONFIRMED = "confirmed"
EDGE_REJECTED = "rejected"

REL_CONTAINS = "contains"
REL_NEAR = "near"
REL_OBSERVES = "observes"
REL_OPERATES_IN = "operates_in"
REL_ADJACENT_TO = "adjacent_to"
REL_FLOW_TO = "flow_to"
REL_CONTROLS = "controls"
REL_ASSIGNED_TO = "assigned_to"
REL_AFFECTS = "affects"
REL_SUPPORTS = "supports"

PRIORITY_SCORE = {
    "critical": 100,
    "high": 70,
    "medium": 40,
    "low": 10,
}