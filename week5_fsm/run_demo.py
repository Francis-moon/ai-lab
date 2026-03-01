from fsm_slot import Slot, SlotStateMachine

def main():
    slot = Slot(slot_id="A-23")
    fsm = SlotStateMachine(slot)

    print("INIT:", fsm.snapshot())

    # 1) FREE -> OCCUPIED
    fsm.occupy()
    print("AFTER occupy:", fsm.snapshot())

    # 2) OCCUPIED -> ILLEGAL（带 reason）
    fsm.detect_illegal(reason="blacklist_plate")
    print("AFTER detect_illegal:", fsm.snapshot())

    # 3) ILLEGAL -> CLEARED（带 evidence）
    fsm.clear(evidence={"img_url": "mock://image/123", "ts": "2026-03-01T00:00:00Z"})
    print("AFTER clear:", fsm.snapshot())

    # 4) CLEARED -> FREE
    fsm.release()
    print("AFTER release:", fsm.snapshot())

    print("\n--- HISTORY ---")
    for h in fsm.get_history():
        print(f"{h.ts} | {h.event} | {h.from_state} -> {h.to_state} | {h.note}")

    # 5) 测试非法触发（应报错）：FREE 状态下 detect_illegal
    print("\n--- INVALID TRIGGER TEST ---")
    try:
        fsm.detect_illegal(reason="should_fail")
    except Exception as e:
        print("Expected error:", type(e).__name__, str(e))


if __name__ == "__main__":
    main()