from typing import Dict, Any
from datetime import datetime

# 模拟：从“空间对象数据库/语义地图”里查看车位状态
_FAKE_SLOT_STATE = {
    1: {"state": "Free", "zone": "A", "last_updated": "2026-02-01T10:00:00"},
    8: {"state": "Occupied", "zone": "A", "last_updated": "2026-02-01T10:10:00"},
    12: {"state": "Illegal", "zone": "B", "last_updated": "2026-02-01T10:20:00"},
}

def get_slot_state(slot_id: int) -> Dict[int, Any]:
    slot_id = slot_id
    data = _FAKE_SLOT_STATE.get(slot_id)
    if not data:
        return {"slot_id": slot_id, "found": False}
    return {
        "slot_id": slot_id,
        "found": True,
    }


def inspect_slot(slot_id: int) -> Dict[int, Any]:
    # 真实系统里：可能触发机器人巡检/调用车位相机等
    now = datetime.now().isoformat()
    state_info = _FAKE_SLOT_STATE.get(slot_id)

    if not state_info:
        return {
            "slot_id": slot_id,
            "found": False,
            "action": "inspect",
            "result": "failed",
            "state": "Unknown",
            "evidence": None,
            "timestamp": now,
        }

    return {
        "slot_id": slot_id,
        "found": True,
        "action": "inspect",
        "result": "success",
        "state": state_info["state"],
        "zone": state_info["zone"],
        "state_last_updated": state_info["last_updated"],
        "evidence": f"inspection_log_{slot_id}_{now}",
        "timestamp": now,
    }


def capture_evidence(slot_id: int, reason: str) -> Dict[int, Any]:
    # 拍照取证
    now = datetime.now().isoformat()
    return {
        "slot_id": slot_id,
        "action": "capture_evidence",
        "reason": reason,
        "photo_id": f"photo_{slot_id}_{now}",
        "timestamp": now,
    }


if __name__ == "__main__":
    # 测试：根据车位号是否找到车位
    print(get_slot_state(1))
    print(get_slot_state(6))
    print(inspect_slot(8))
    print(inspect_slot(12))
    print(capture_evidence(12, "Illegal parking"))
