from __future__ import annotations
from typing import Dict, List, Tuple

from .models import Slot, Zone, SlotState
from .utils import log, log_error


def seed_demo_data() -> Tuple[Dict[str, Zone], Dict[int, Slot]]:
    """
    Creates demo parking objects in memory (no DB in week 1).
    Returns:
        zones: dict of zone_id -> Zone
        slots: dict of slot_id -> Slot
    """
    zones = {
        'A': Zone(zone_id='A', name="A区"),
        'B': Zone(zone_id='B', name="B区"),
    }

    # Create 10 slots in each zone
    slots: Dict[int, Slot] = {}
    for i in range(1, 11):
        slot_id = i
        slots[slot_id] = Slot(slot_id=slot_id, zone_id='A', state=SlotState.FREE)

    for i in range(11, 21):
        slot_id = i
        slots[slot_id] = Slot(slot_id=slot_id, zone_id='B', state=SlotState.FREE)
    
    # Mark a few slots as occupied or reserved or error for demo
    slots[2].state = SlotState.OCCUPIED
    slots[5].state = SlotState.RESERVED
    slots[8].state = SlotState.ILLEGAL
    slots[12].state = SlotState.OCCUPIED
    slots[15].state = SlotState.RESERVED
    log("Demo data seeded: 2 zones, 20 slots (some occupied/reserved/error)")

    return zones, slots


def inspect_slot(slots: Dict[int, Slot], slot_id: int) -> str:
    # inspect a slot by id, return its status as string and Log it.
    if slot_id not in slots:
        raise KeyError(f"Slot not found: {slot_id:02d}")
    
    slot = slots[slot_id]
    log(f"Inspecting slot {slot_id:02d}: {slot.state}")
    return f"{slot_id:02d} inspected, state={slot.state}"


def list_slots_by_zone(slots: Dict[int, Slot], zone_id: str) -> List[Slot]:
    """Returns all slots in the specified zone."""
    return [slot for slot in slots.values() if slot.zone_id == zone_id]


def list_free_slots(slots: Dict[int, Slot], zone_id: str | None = None) -> List[Slot]:
    """Returns all free slots, optionally filtered by zone."""
    res = []
    for slot in slots.values():
        if slot.state != SlotState.FREE:
            continue
        if zone_id and slot.zone_id != zone_id:
            continue
        res.append(slot)
    return res


def set_slot_state(slots: Dict[int, Slot], slot_id: int, new_state: SlotState) -> None:
    """Change the state of a slot. (week 1: no rules, just set).
    Logs an error if the slot_id is invalid.
    """
    if slot_id not in slots:
        log_error(f"Slot ID {slot_id:02d} not found")
        return
    old_state = slots[slot_id].state
    # 规则1: reserved不能由occupied变过来
    if old_state == SlotState.OCCUPIED and new_state == SlotState.RESERVED:
        log_error(f"Invalid state change: OCCUPIED -> RESERVED is not allowed for slot {slot_id:02d}")
        return
    # 规则2: 只有OCCUPIED才能变成ILLEGAL
    if new_state == SlotState.ILLEGAL and old_state != SlotState.OCCUPIED:
        log_error(f"Invalid state change: Only OCCUPIED can become ILLEGAL for slot {slot_id:02d}")
        return
    slots[slot_id].state = new_state
    log(f"Slot {slot_id:02d} state updated: {old_state} -> {new_state}")

if __name__ == '__main__':
    zones, slots = seed_demo_data()
    print(inspect_slot(slots, 2))
    print(inspect_slot(slots, 3))
    print(inspect_slot(slots, 8))
    print('Slots in zone A:')
    for slot in list_slots_by_zone(slots, 'A'):
        print(f"slot_id={slot.slot_id:02d}, state='{slot.state.value}'")
    print('Free slots:')
    for slot in list_free_slots(slots):
        print(f"slot_id={slot.slot_id:02d}, zone_id={slot.zone_id}, state='{slot.state.value}'")
    set_slot_state(slots, 5, SlotState.OCCUPIED)  # valid change
    set_slot_state(slots, 2, SlotState.RESERVED)  # invalid change
    set_slot_state(slots, 8, SlotState.FREE)      # valid change
    set_slot_state(slots, 12, SlotState.ILLEGAL) # valid change
    set_slot_state(slots, 15, SlotState.ILLEGAL) # invalid change
    