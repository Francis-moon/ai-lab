"""
真正理解 JSON = 结构化业务数据，而不是“格式”。
这一步是未来做 事件 → 状态 → 任务闭环 的数据基础。
"""
import json

def pretty(obj):
    """把Python对象转换成漂亮的JSON字符串"""
    print(json.dumps(obj, indent=2, ensure_ascii=False))

def main():
    # 1) JSON对象（字典）
    slot = {
        "slot_id": 12,
        "state": "Free",
        "zone": "A",
        "history": [
            {"event": "Cleared", "ts": "2026-02-22T10:00:00+08:00"},
            {"event": "Occupied", "ts": "2026-02-22T9:00:00+08:00"},
        ],
    }

    # 2) 访问字段
    print("slot_id:", slot["slot_id"])
    print("last_event:", slot["history"][0]["event"])   # 注意：history[0]是最新的事件，因为我们把新事件插入到列表开头了。

    # 3) 更新字段（模拟状态变化）
    slot["state"] = "Occupied"
    slot["history"].insert(0, {"event": "Occupied", "ts": "2026-02-22T11:00:00+08:00"})

    # 4) 打印漂亮的JSON字符串
    pretty(slot)

    # 5） 字符串 <-> JSON对象
    s = '{"event": "Illegal Parking", "target": "Slot 12"}'
    e = json.loads(s)  # JSON字符串 -> Python对象
    print("Parsed event type:", e["event"])

    back = json.dumps(e, ensure_ascii=False)  # Python对象 -> JSON字符串
    print("Back to JSON string:", back)

if __name__ == "__main__":
    main()
    