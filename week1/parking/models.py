from dataclasses import dataclass
from enum import Enum

class SlotState(str, Enum):
    FREE = "free"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    ERROR = "error"

# 车位实体
@dataclass
class Slot:
    slot_id: int
    zone_id: str
    state: SlotState = SlotState.FREE

    def __str__(self):
        return f"Slot {self.slot_id} in Zone {self.zone_id} is {self.state}"

    def occupy(self):
        if self.state == SlotState.FREE:
            self.state = SlotState.OCCUPIED
        else:
            raise ValueError(f"Cannot occupy slot {self.slot_id} because it is {self.state}")

    def clear(self):
        if self.state in (SlotState.OCCUPIED, SlotState.RESERVED):
            self.state = SlotState.FREE
        else:
            raise ValueError(f"Cannot clear slot {self.slot_id} because it is {self.state}")

# 区域实体
@dataclass
class Zone:
    zone_id: str
    name: str

    def __str__(self):
        return f"Zone {self.zone_id} ({self.name})"

if __name__ == '__main__':
    slot1 = Slot(slot_id=1, zone_id='A1')
    slot2 = Slot(slot_id=2, zone_id='A2', state=SlotState.OCCUPIED)
    slot3 = Slot(slot_id=3, zone_id='A1', state=SlotState.RESERVED)
    print(slot1)
    slot1.occupy()
    print(slot1)
    print(slot1.slot_id+8)
    print(slot2)
    print(slot3)
    zone_A1 = Zone(zone_id='A1', name="地下A1区")
    zone_A2 = Zone(zone_id='A2', name="地下A2区")
    print(zone_A1)
    print(zone_A2.name)
    print(SlotState.FREE)
    print(SlotState.OCCUPIED.value)
    for slot in [slot1, slot2, slot3]:
        if slot.zone_id == zone_A1.zone_id and zone_A1.name == "地下A1区":
            print(slot.slot_id)
