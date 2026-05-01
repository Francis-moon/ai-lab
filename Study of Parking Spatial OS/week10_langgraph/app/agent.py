# 用langgraph做一个简单图：读取事件 -> 判断策略 -> 执行工具 -> 输出结果
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from .tools import get_slot, update_slot_state, create_task, mark_event_processed


class AgentState(TypedDict):
    event_id: str
    event_type: str
    slot_id: Optional[str]
    zone: str
    source: str

    current_slot_state: Optional[str]
    decision: Optional[str]
    task_result: Optional[dict]
    slot_update_result: Optional[dict]
    final_result: Optional[dict]
    error: Optional[str]


def load_context(state: AgentState) -> AgentState:
    if state.get("slot_id"):
        slot = get_slot(state["slot_id"])
        state["current_slot_state"] = slot["state"]
    return state


def decide_action(state: AgentState) -> AgentState:
    event_type = state["event_type"]
    slot_state = state.get("current_slot_state")

    if event_type == "illegal_parking_detected":
        if slot_state != "illegal":
            state["decision"] = "update_to_illegal_and_create_inspection_task"
        else:
            state["decision"] = "create_inspection_task"

    elif event_type == "lane_blocked_detected":
        state["decision"] = "create_clearance_task"

    elif event_type == "slot_freed_detected":
        state["decision"] = "update_to_free"

    else:
        state["decision"] = "mark_processed_only"

    return state


def execute_action(state: AgentState) -> AgentState:
    decision = state["decision"]
    slot_id = state.get("slot_id")
    zone = state["zone"]

    if decision == "update_to_illegal_and_create_inspection_task":
        state["slot_update_result"] = update_slot_state(slot_id, "illegal")
        state["task_result"] = create_task(
            task_type="inspect_illegal_parking",
            slot_id=slot_id,
            zone=zone,
            assignee="robot",
            priority="high"
        )

    elif decision == "create_inspection_task":
        state["task_result"] = create_task(
            task_type="inspect_illegal_parking",
            slot_id=slot_id,
            zone=zone,
            assignee="robot",
            priority="high"
        )

    elif decision == "create_clearance_task":
        state["task_result"] = create_task(
            task_type="clear_blocked_lane",
            slot_id=slot_id or "UNKNOWN",
            zone=zone,
            assignee="human",
            priority="high"
        )

    elif decision == "update_to_free":
        state["slot_update_result"] = update_slot_state(slot_id, "free")

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
    def wrapper(state: AgentState) -> AgentState:
        try:
            return func(state)
        except Exception as e:
            state["error"] = str(e)
            return state
    return wrapper


def route_after_load(state: AgentState):
    if state.get("error"):
        return "handle_error"
    return "decide_action"


def route_after_decide(state: AgentState):
    if state.get("error"):
        return "handle_error"
    return "execute_action"


def route_after_execute(state: AgentState):
    if state.get("error"):
        return "handle_error"
    return "finalize"


def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node("load_context", safe_node(load_context))
    graph.add_node("decide_action", safe_node(decide_action))
    graph.add_node("execute_action", safe_node(execute_action))
    graph.add_node("finalize", safe_node(finalize))
    graph.add_node("handle_error", handle_error)

    graph.set_entry_point("load_context")

    graph.add_conditional_edges("load_context", route_after_load, {
        "decide_action": "decide_action",
        "handle_error": "handle_error",
    })

    graph.add_conditional_edges("decide_action", route_after_decide, {
        "execute_action": "execute_action",
        "handle_error": "handle_error",
    })

    graph.add_conditional_edges("execute_action", route_after_execute, {
        "finalize": "finalize",
        "handle_error": "handle_error",
    })

    graph.add_edge("finalize", END)
    graph.add_edge("handle_error", END)

    return graph.compile()


agent_app = build_agent()