from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

from transitions import Machine


# ----------------------------
# 1) 业务状态定义
# ----------------------------
STATES = ["FREE", "OCCUPIED", "ILLEGAL", "CLEARED"]


@dataclass
class SlotHistoryItem:
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
                ts=datetime.utcnow().isoformat(timespec="seconds") + "Z",
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
            states=STATES,
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