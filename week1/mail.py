"""
一个极简版的 Parking Spatial OS 控制台模拟器
它已经包含了你战略文档中的三个核心概念：
空间对象Slot / Zone
状态FREE / OCCUPIED / ILLEGAL / RESERVED
操作Inspect / State Update
"""
from __future__ import annotations
from typing import Dict, List, Tuple

from parking.models import Slot, Zone, SlotState
from parking.services import (
    seed_demo_data, 
    inspect_slot, 
    list_slots_by_zone, 
    list_free_slots,
    set_slot_state,
)
from parking.utils import log, log_error


def print_zone_summary(zones, slots) -> None:
    log("Parking Zone Summary:")
    for zid, z in zones.items():
        zone_slots = list_slots_by_zone(slots, zid)
        free_count = len([s for s in zone_slots if s.state == SlotState.FREE])
        occ_count = len([s for s in zone_slots if s.state == SlotState.OCCUPIED])
        ill_count = len([s for s in zone_slots if s.state == SlotState.ILLEGAL])
        res_count = len([s for s in zone_slots if s.state == SlotState.RESERVED])
        print(f"{z.name}({zid}):total={len(zone_slots)}, free={free_count}, occupied={occ_count}, illegal={ill_count}, reserved={res_count}")
        

def step1_demo(zones, slots) -> None:
    # Step 1: basic prints + inspect
    print_zone_summary(zones, slots)
    log("Step 1: demo inspect")
    print(inspect_slot(slots, 1))
    print(inspect_slot(slots, 2))
    print(inspect_slot(slots, 5))
    print(inspect_slot(slots, 8))
    print(inspect_slot(slots, 12))

def step2_queries(zones, slots) -> None:
    # Step 2: list free slots, zone filter
    log("Step 2: query free slots")
    free_all = list_free_slots(slots)
    print(f"Total free slots: {[s.slot_id for s in free_all]}")
    
    free_a = list_free_slots(slots, zone_id='A')
    print(f"Free slots in A区: {[s.slot_id for s in free_a]}")
    # HW4: Count free slots in each zone, return a dict of zone_id -> free_count
    print(f"HW4: Free slots in zoneA: {len(free_a)}")

def step3_state_update(zones, slots) -> None:
    # Step 3: update slot state and re-check summaries
    log("Step 3: update slot state and re-check")
    set_slot_state(slots, 3, SlotState.OCCUPIED)
    # set_slot_state(slots, 3, SlotState.clear if hasattr(SlotState, "CLEARED") else SlotState.FREE)  # safe fallback
    # If you want strictness, just do: set_slot_state(slots, "B-04", SlotState.FREE)
    slots[3].clear()  # demo clear method in Slot model
    print(inspect_slot(slots, 3))
    set_slot_state(slots, 21, SlotState.FREE)
    set_slot_state(slots, 12, SlotState.ILLEGAL)

def week1_homework(slots) -> None:
    """
    Homework checklish for week 1.
    You will edit this function during the week.
    """
    log("=== Week 1 Homework ===")
    # HW1: Create a fucntion that returns illegal slots list
    illegal_slots = [slot for slot in slots.values() if slot.state == SlotState.ILLEGAL]
    print(f"HW1 Illegal slots: {[s.slot_id for s in illegal_slots]}")

    # HW2: Count slots by state using a dict (state -> count)
    counts = {}
    for s in slots.values():
        counts[s.state] = counts.get(s.state, 0) + 1
    print(f"HW2: Slot counts by state: {counts}")

    # HW3: pick one slot, toggle between FREE and OCCUPIED 3 times
    target = 11
    for i in range(3):
        new_state = SlotState.OCCUPIED if slots[target].state == SlotState.FREE else SlotState.FREE
        set_slot_state(slots, target, new_state)
        print(f"HW3:After toggle {i+1}, slot {target:02d} state: {slots[target].state}")

    # HW5: Support input a slot_id and inspect it, print the result. (bonus: support command line input)
    slot_id = input("Enter slot id: ")
    inspect_slot(slots, int(slot_id))

if __name__ == '__main__':
    log("Booting Week 1 template...")
    zones, slots = seed_demo_data()

    step1_demo(zones, slots)
    step2_queries(zones, slots)
    step3_state_update(zones, slots)
    week1_homework(slots)

    log("Done.")