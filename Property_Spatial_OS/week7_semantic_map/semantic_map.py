from typing import Dict, List, Optional
from models import Zone, Lane, Slot, SlotState, SlotType


class SemanticMap:
    def __init__(self):
        self.zones: Dict[str, Zone] = {}
        self.lanes: Dict[str, Lane] = {}
        self.slots: Dict[str, Slot] = {}

    # ===== 注册对象 =====
    def add_zone(self, zone: Zone):
        self.zones[zone.zone_id] = zone

    def add_lane(self, lane: Lane):
        if lane.zone_id not in self.zones:
            raise ValueError(f"Zone不存在: {lane.zone_id}")
        self.lanes[lane.lane_id] = lane
        self.zones[lane.zone_id].lane_ids.append(lane.lane_id)

    def add_slot(self, slot: Slot):
        if slot.zone_id not in self.zones:
            raise ValueError(f"Zone不存在: {slot.zone_id}")
        if slot.lane_id not in self.lanes:
            raise ValueError(f"Lane不存在: {slot.lane_id}")
        self.slots[slot.slot_id] = slot
        self.lanes[slot.lane_id].slot_ids.append(slot.slot_id)

    # ===== 获取对象 =====
    def get_zone(self, zone_id: str) -> Optional[Zone]:
        return self.zones.get(zone_id)

    def get_lane(self, lane_id: str) -> Optional[Lane]:
        return self.lanes.get(lane_id)

    def get_slot(self, slot_id: str) -> Optional[Slot]:
        return self.slots.get(slot_id)

    # ===== 关系查询 =====
    def get_lanes_by_zone(self, zone_id: str) -> List[Lane]:
        zone = self.get_zone(zone_id)
        if not zone:
            return []
        return [self.lanes[lane_id] for lane_id in zone.lane_ids]

    def get_slots_by_lane(self, lane_id: str) -> List[Slot]:
        lane = self.get_lane(lane_id)
        if not lane:
            return []
        return [self.slots[slot_id] for slot_id in lane.slot_ids]

    def get_slots_by_zone(self, zone_id: str) -> List[Slot]:
        slots = []
        for lane in self.get_lanes_by_zone(zone_id):
            slots.extend(self.get_slots_by_lane(lane.lane_id))
        return slots

    def get_zone_of_slot(self, slot_id: str) -> Optional[Zone]:
        slot = self.get_slot(slot_id)
        if not slot:
            return None
        return self.get_zone(slot.zone_id)

    def get_lane_of_slot(self, slot_id: str) -> Optional[Lane]:
        slot = self.get_slot(slot_id)
        if not slot:
            return None
        return self.get_lane(slot.lane_id)

    def ask_slot_relation(self, slot_id: str) -> Optional[Dict[str, str]]:
        slot = self.get_slot(slot_id)
        if not slot:
            return None

        lane = self.get_lane_of_slot(slot_id)
        zone = self.get_zone_of_slot(slot_id)

        return {
            "slot_id": slot.slot_id,
            "lane_id": lane.lane_id if lane else "N/A",
            "zone_id": zone.zone_id if zone else "N/A",
            "slot_state": slot.state.value,
        }

    def ask_slot_relation_interactive(self):
        raw_input = input("\n请输入车位号 Slot-: ").strip()
        if not raw_input:
            print("输入为空，请重新运行后输入车位号。")
            return

        slot_id = raw_input if raw_input.startswith("Slot-") else f"Slot-{raw_input}"
        qa_result = self.ask_slot_relation(slot_id)

        if not qa_result:
            print(f"未找到车位: {slot_id}")
            return

        print("\n=== 对象关系问答结果 ===")
        print(f"输入: {qa_result['slot_id']}")
        print(f"属于Lane: {qa_result['lane_id']}")
        print(f"属于Zone: {qa_result['zone_id']}")
        print(f"当前状态: {qa_result['slot_state']}")

    # ===== 业务查询 =====
    def get_free_slots_by_zone(self, zone_id: str) -> List[Slot]:
        return [
            slot for slot in self.get_slots_by_zone(zone_id)
            if slot.state == SlotState.FREE
        ]

    def get_free_charging_slots_by_zone(self, zone_id: str) -> List[Slot]:
        return [
            slot for slot in self.get_slots_by_zone(zone_id)
            if slot.state == SlotState.FREE and slot.slot_type == SlotType.CHARGING
        ]

    def get_illegal_slots(self) -> List[Slot]:
        return [
            slot for slot in self.slots.values()
            if slot.state == SlotState.ILLEGAL
        ]

    def show_map_summary(self):
        print("\n=== 语义地图概览 ===")
        for zone in self.zones.values():
            print(f"[Zone] {zone.zone_id} - {zone.name}")
            lanes = self.get_lanes_by_zone(zone.zone_id)
            for lane in lanes:
                print(
                    f"  [Lane] {lane.lane_id} - {lane.name} - "
                    f"direction={lane.direction.value} - state={lane.state.value}"
                )
                slots = self.get_slots_by_lane(lane.lane_id)
                for slot in slots:
                    print(
                        f"    [Slot] {slot.slot_id} - "
                        f"type={slot.slot_type.value} - state={slot.state.value}"
                    )