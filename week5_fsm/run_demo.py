from fsm_slot_lane import Lane, LaneStateMachine, Slot, SlotStateMachine, export_history

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

    # 3) ILLEGAL -> CLEARED
    fsm.clear(evidence={"img_url": "mock://image/123", "ts": "2026-03-01T00:00:00Z"})
    # fsm.clear() # 这里先不传 evidence，看看默认值
    print("AFTER clear:", fsm.snapshot())

    # 4) CLEARED -> FREE
    fsm.release()
    print("AFTER release:", fsm.snapshot())

    print("\n--- HISTORY ---")
    for h in fsm.get_history():
        print(f"{h.ts} | {h.event} | {h.from_state} -> {h.to_state} | {h.note}")
    export_file = export_history(slot, output_dir="week5_fsm")
    print(f"\nHistory exported: {export_file}")

    # 5) 测试非法触发（应报错）：FREE 状态下 detect_illegal
    print("\n--- INVALID TRIGGER TEST ---")
    try:
        fsm.detect_illegal(reason="should_fail")
    except Exception as e:
        print("Expected error:", type(e).__name__, str(e))

    print("\n================ LANE BLOCKED DEMO ================")
    lane = Lane(lane_id="A-1")
    lane_fsm = LaneStateMachine(lane)

    print("INIT:", lane_fsm.snapshot())

    # 1) CLEAR -> BLOCKED
    lane_fsm.block(reason="accident_vehicle")
    print("AFTER block:", lane_fsm.snapshot())

    # 2) BLOCKED -> CLEARED
    lane_fsm.clear()
    print("AFTER clear:", lane_fsm.snapshot())

    # 3) CLEARED -> CLEAR
    lane_fsm.release()
    print("AFTER release:", lane_fsm.snapshot())

    # 4) * -> CLEAR
    lane_fsm.reset()
    print("AFTER reset:", lane_fsm.snapshot())

    print("\n--- LANE HISTORY ---")
    for h in lane_fsm.get_history():
        print(f"{h.ts} | {h.event} | {h.from_state} -> {h.to_state} | {h.note}")


if __name__ == "__main__":
    main()
