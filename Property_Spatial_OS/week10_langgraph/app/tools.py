import requests

BASE_URL = "http://127.0.0.1:8000"


def get_slot(slot_id: str):
    resp = requests.get(f"{BASE_URL}/slots/{slot_id}", timeout=10)
    if resp.status_code != 200:
        raise ValueError(f"Slot {slot_id} not found")
    return resp.json()


def update_slot_state(slot_id: str, state: str):
    resp = requests.put(
        f"{BASE_URL}/slots/{slot_id}/state",
        json={"state": state},
        timeout=10
    )
    if resp.status_code != 200:
        raise ValueError(f"Failed to update slot state: {resp.text}")
    return resp.json()


def create_task(task_type: str, slot_id: str, zone: str, assignee: str, priority: str):
    payload = {
        "task_id": f"{task_type}-{slot_id}",
        "task_type": task_type,
        "slot_id": slot_id,
        "zone": zone,
        "assignee": assignee,
        "priority": priority,
    }
    resp = requests.post(f"{BASE_URL}/tasks", json=payload, timeout=10)
    if resp.status_code != 200:
        raise ValueError(f"Failed to create task: {resp.text}")
    return resp.json()


def mark_event_processed(event_id: str):
    resp = requests.put(f"{BASE_URL}/events/{event_id}/processed", timeout=10)
    if resp.status_code != 200:
        raise ValueError(f"Failed to mark event processed: {resp.text}")
    return resp.json()