# 这版 Agent 输出的是更贴近宜泊的任务参数：
# 包括 preferred_assignee、sla_minutes、zone_heat、fallback_chain
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from .tools import get_slot, update_slot_state, create_task, mark_event_processed, get_zone_state


class AgentState(TypedDict):
    event_id: str
    event_type: str
    slot_id: Optional[str]
    zone: str
    source: str

    current_slot_state: Optional[str]
    zone_heat: Optional[int]
    decision: Optional[str]
    task_payload: Optional[dict]
    task_result: Optional[dict]
    slot_update_result: Optional[dict]
    final_result: Optional[dict]
    error: Optional[str]


def load_context(state: AgentState) -> AgentState:
    if state.get("slot_id"):
        slot = get_slot(state["slot_id"])
        state["current_slot_state"] = slot["state"]

    zone_state = get_zone_state(state["zone"])
    state["zone_heat"] = zone_state["heat"]
    return state


def decide_action(state: AgentState) -> AgentState:
    event_type = state["event_type"]
    slot_state = state.get("current_slot_state")
    zone_heat = state.get("zone_heat", 1)

    if event_type == "illegal_parking_detected":
        if slot_state != "illegal":
            state["decision"] = "update_and_dispatch_inspection"
        else:
            state["decision"] = "dispatch_inspection"

        state["task_payload"] = {
            "task_id": f"{state['event_id']}-inspect",
            "task_type": "inspect_illegal_parking",
            "slot_id": state["slot_id"],
            "zone": state["zone"],
            "preferred_assignee": "robot",
            "priority": "high" if zone_heat >= 7 else "medium",
            "sla_minutes": 5 if zone_heat >= 7 else 15,
            "zone_heat": zone_heat,
            "fallback_chain": "robot,human,cloud_operator"
        }

    elif event_type == "lane_blocked_detected":
        state["decision"] = "dispatch_clearance"
        state["task_payload"] = {
            "task_id": f"{state['event_id']}-clear",
            "task_type": "clear_blocked_lane",
            "slot_id": state["slot_id"],
            "zone": state["zone"],
            "preferred_assignee": "human",
            "priority": "critical",
            "sla_minutes": 3,
            "zone_heat": zone_heat,
            "fallback_chain": "human,cloud_operator,robot"
        }

    elif event_type == "slot_freed_detected":
        state["decision"] = "update_to_free"

    else:
        state["decision"] = "mark_only"

    return state


def execute_action(state: AgentState) -> AgentState:
    decision = state["decision"]

    if decision == "update_and_dispatch_inspection":
        state["slot_update_result"] = update_slot_state(state["slot_id"], "illegal")
        state["task_result"] = create_task(state["task_payload"])

    elif decision == "dispatch_inspection":
        state["task_result"] = create_task(state["task_payload"])

    elif decision == "dispatch_clearance":
        state["task_result"] = create_task(state["task_payload"])

    elif decision == "update_to_free":
        state["slot_update_result"] = update_slot_state(state["slot_id"], "free")

    return state


def finalize(state: AgentState) -> AgentState:
    mark_event_processed(state["event_id"])
    state["final_result"] = {
        "event_id": state["event_id"],
        "decision": state["decision"],
        "task_result": state.get("task_result"),
        "slot_update_result": state.get("slot_update_result"),
        "status": "success"
    }
    return state


def handle_error(state: AgentState) -> AgentState:
    state["final_result"] = {
        "event_id": state["event_id"],
        "status": "failed",
        "error": state.get("error", "unknown error")
    }
    return state


def safe_node(func):
    def wrapper(state: AgentState):
        try:
            return func(state)
        except Exception as e:
            state["error"] = str(e)
            return state
    return wrapper


def route_after(state):
    return "handle_error" if state.get("error") else None


def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node("load_context", safe_node(load_context))
    graph.add_node("decide_action", safe_node(decide_action))
    graph.add_node("execute_action", safe_node(execute_action))
    graph.add_node("finalize", safe_node(finalize))
    graph.add_node("handle_error", handle_error)

    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "decide_action")
    graph.add_edge("decide_action", "execute_action")
    graph.add_edge("execute_action", "finalize")
    graph.add_edge("finalize", END)
    graph.add_edge("handle_error", END)

    return graph.compile()


agent_app = build_agent()