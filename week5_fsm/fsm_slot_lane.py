from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
china_tz = timezone(timedelta(hours=8))
from typing import List, Dict, Any, Optional

from transitions import Machine


# ----------------------------
# 1) 业务状态定义
# ----------------------------

@dataclass
class SlotHistoryItem:
    ts: str
    event: str
    from_state: str
    to_state: str
    note: str = ""


@dataclass
class LaneHistoryItem:
    ts: str
    event: str
    from_state: str
    to_state: str
    note: str = ""


@dataclass
class Slot:
    """
    Slot（车位）= 你们战略里“空间对象模型”的最小对象之一，
    这里先聚焦“状态机与事件系统”。
    """
    slot_id: str
    state: str = "FREE"
    history: List[SlotHistoryItem] = field(default_factory=list)

    # 可选：用于挂载“证据”或“异常描述”
    last_evidence: Optional[Dict[str, Any]] = None
    last_illegal_reason: Optional[str] = None

    def add_history(self, event: str, from_state: str, to_state: str, note: str = "") -> None:
        self.history.append(
            SlotHistoryItem(
                ts=datetime.now(china_tz).isoformat(timespec="seconds").replace("+00:00", "Z"),
                event=event,
                from_state=from_state,
                to_state=to_state,
                note=note,
            )
        )


@dataclass
class Lane:
    lane_id: str
    state: str = "CLEAR"
    history: List[LaneHistoryItem] = field(default_factory=list)
    last_block_reason: Optional[str] = None

    def add_history(self, event: str, from_state: str, to_state: str, note: str = "") -> None:
        self.history.append(
            LaneHistoryItem(
                ts=datetime.now(china_tz).isoformat(timespec="seconds").replace("+00:00", "Z"),
                event=event,
                from_state=from_state,
                to_state=to_state,
                note=note,
            )
        )


class SlotStateMachine:
    """
    把 transitions 的 Machine 包一层，避免外部直接改 state。
    """
    SLOT_STATES = ["FREE", "OCCUPIED", "ILLEGAL", "CLEARED"]

    def __init__(self, slot: Slot):
        self.slot = slot

        # 事件迁移表：只允许这些合法迁移
        transitions = [
            # FREE -> OCCUPIED
            {"trigger": "occupy", "source": "FREE", "dest": "OCCUPIED"},
            # OCCUPIED -> ILLEGAL（检测到异常停车）
            {"trigger": "detect_illegal", "source": "OCCUPIED", "dest": "ILLEGAL"},
            # ILLEGAL -> CLEARED（已处置：驱离/通知/取证完成）
            {"trigger": "clear", "source": "ILLEGAL", "dest": "CLEARED"},
            # CLEARED -> FREE（复核确认恢复正常）
            {"trigger": "release", "source": "CLEARED", "dest": "FREE"},
            # 兜底：任何状态 -> FREE（人工重置）
            {"trigger": "reset", "source": "*", "dest": "FREE"},
        ]

        self.machine = Machine(
            model=self,
            states=self.SLOT_STATES,
            initial=slot.state,
            transitions=transitions,
            before_state_change="before_change",
            after_state_change="after_change",
            send_event=True,  # 允许回调里拿到 event 信息
            ignore_invalid_triggers=False,  # 触发非法事件直接报错（很重要）
        )

    # ----------------------------
    # 2) 回调：迁移前/后动作
    # ----------------------------
    def before_change(self, event):
        """
        迁移前：记录 from_state、捕捉一些上下文
        """
        self._from_state = self.state  # transitions 会把当前状态放在 model.state
        self._event_name = event.event.name
        if self._event_name == "clear" and event.kwargs.get("evidence") is None:
            raise ValueError("clear requires evidence")

    def after_change(self, event):
        """
        迁移后：写审计日志、同步回 Slot 实体
        """
        to_state = self.state
        from_state = getattr(self, "_from_state", "UNKNOWN")
        ev = getattr(self, "_event_name", "UNKNOWN")

        note = ""
        if ev == "detect_illegal":
            reason = event.kwargs.get("reason", "unknown")
            self.slot.last_illegal_reason = reason
            note = f"illegal_reason={reason}"

        if ev == "clear":
            evidence = event.kwargs.get("evidence")
            if evidence:
                self.slot.last_evidence = evidence
                note = f"evidence_keys={list(evidence.keys())}"

        # 写 history（可审计）
        self.slot.add_history(event=ev, from_state=from_state, to_state=to_state, note=note)

        # 同步 Slot 的 state（外部只看 Slot.state）
        self.slot.state = to_state

    # ----------------------------
    # 3) 对外暴露的安全接口
    # ----------------------------
    def get_state(self) -> str:
        return self.slot.state

    def get_history(self) -> List[SlotHistoryItem]:
        return self.slot.history

    def snapshot(self) -> Dict[str, Any]:
        return {
            "slot_id": self.slot.slot_id,
            "state": self.slot.state,
            "last_illegal_reason": self.slot.last_illegal_reason,
            "last_evidence": self.slot.last_evidence,
            "history_len": len(self.slot.history),
        }


class LaneStateMachine:
    """
    Lane 状态机：模拟通道堵塞 LaneBlocked 事件。
    """

    LANE_STATES = ["CLEAR", "BLOCKED", "CLEARED"]

    def __init__(self, lane: Lane):
        self.lane = lane
        transitions = [
            {"trigger": "block", "source": "CLEAR", "dest": "BLOCKED"},
            {"trigger": "clear", "source": "BLOCKED", "dest": "CLEARED"},
            {"trigger": "release", "source": "CLEARED", "dest": "CLEAR"},
            {"trigger": "reset", "source": "*", "dest": "CLEAR"},
        ]

        self.machine = Machine(
            model=self,
            states=self.LANE_STATES,
            initial=lane.state,
            transitions=transitions,
            before_state_change="before_change",
            after_state_change="after_change",
            send_event=True,
            ignore_invalid_triggers=False,
        )

    def before_change(self, event):
        self._from_state = self.state
        self._event_name = event.event.name
        if self._event_name == "block" and event.kwargs.get("reason") is None:
            raise ValueError("block requires reason")

    def after_change(self, event):
        to_state = self.state
        from_state = getattr(self, "_from_state", "UNKNOWN")
        ev = getattr(self, "_event_name", "UNKNOWN")

        note = ""
        if ev == "block":
            reason = event.kwargs.get("reason", "unknown")
            self.lane.last_block_reason = reason
            note = f"block_reason={reason}"

        self.lane.add_history(event=ev, from_state=from_state, to_state=to_state, note=note)
        self.lane.state = to_state

    def get_state(self) -> str:
        return self.lane.state

    def get_history(self) -> List[LaneHistoryItem]:
        return self.lane.history

    def snapshot(self) -> Dict[str, Any]:
        return {
            "lane_id": self.lane.lane_id,
            "state": self.lane.state,
            "last_block_reason": self.lane.last_block_reason,
            "history_len": len(self.lane.history),
        }

    # ----------------------------
    # 4) 导出历史记录为 JSON
    # ----------------------------
def export_history(slot: Slot, output_dir: str = ".") -> str:
    output_path = Path(output_dir) / f"history_{slot.slot_id}.json"
    payload = [
        {
            "ts": item.ts,
            "event": item.event,
            "from": item.from_state,
            "to": item.to_state,
            "note": item.note,
        }
        for item in slot.history
    ]
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(output_path)
