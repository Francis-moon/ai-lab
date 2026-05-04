import requests

BASE_URL = "http://127.0.0.1:8000"


def get_slot(slot_id: str):
    resp = requests.get(f"{BASE_URL}/slots/{slot_id}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def update_slot_state(slot_id: str, state: str):
    resp = requests.put(
        f"{BASE_URL}/slots/{slot_id}/state",
        json={"state": state},
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def create_task(payload: dict):
    resp = requests.post(f"{BASE_URL}/tasks", json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def mark_event_processed(event_id: str):
    resp = requests.put(f"{BASE_URL}/events/{event_id}/processed", timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_zone_state(zone: str):
    resp = requests.get(f"{BASE_URL}/zones/{zone}", timeout=10)
    resp.raise_for_status()
    return resp.json()