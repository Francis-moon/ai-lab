POLICIES = {
    ("illegal_parking_detected", "remote_verify", "false_alarm"): {
        "action": "close_case",
        "next_state": "closed",
        "reason": "remote_false_alarm"
    },

    ("illegal_parking_detected", "remote_verify", "confirmed_illegal"): {
        "action": "create_task",
        "next_state": "confirmed",
        "task_type": "capture_evidence",
        "priority": "high",
        "sla_minutes": 5,
        "fallback_chain": "robot,human,cloud_operator"
    },

    ("illegal_parking_detected", "remote_verify", "low_confidence"): {
        "action": "create_task",
        "next_state": "verifying",
        "task_type": "robot_recheck",
        "priority": "high",
        "sla_minutes": 8,
        "fallback_chain": "robot,human"
    },

    ("illegal_parking_detected", "robot_recheck", "cleared"): {
        "action": "close_case",
        "next_state": "closed",
        "reason": "robot_recheck_cleared"
    },

    ("illegal_parking_detected", "robot_recheck", "still_present"): {
        "action": "create_task",
        "next_state": "confirmed",
        "task_type": "capture_evidence",
        "priority": "high",
        "sla_minutes": 5,
        "fallback_chain": "robot,human"
    },

    ("illegal_parking_detected", "capture_evidence", "evidence_captured"): {
        "action": "create_task",
        "next_state": "waiting",
        "task_type": "notify_property",
        "priority": "medium",
        "sla_minutes": 10,
        "fallback_chain": "cloud_operator,human"
    },

    ("lane_blocked_detected", "clear_blocked_lane", "cleared"): {
        "action": "close_case",
        "next_state": "closed",
        "reason": "lane_cleared"
    },

    ("lane_blocked_detected", "clear_blocked_lane", "failed"): {
        "action": "create_task",
        "next_state": "escalated",
        "task_type": "supervisor_escalation",
        "priority": "critical",
        "sla_minutes": 2,
        "fallback_chain": "human,cloud_operator"
    }
}


def get_policy(case_type: str, task_type: str, outcome_type: str):
    return POLICIES.get((case_type, task_type, outcome_type))
