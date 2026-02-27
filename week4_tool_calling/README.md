第4周你必须理解的核心点

核心点1：Tool Calling 不是“让模型写代码”
而是让模型输出一个结构化“调用请求”，你本地去执行，再把结果回传给模型继续推理。
这就是“可控的执行链”。（Responses API 支持函数调用与对话状态衔接）

核心点2：为什么用 previous_response_id
它让第二次请求“接着第一次的上下文继续”，形成一次任务的多轮执行闭环。

核心点3：为什么强制 json_object
你后面要接状态机/事件系统/数据库，必须保证输出可解析。Structured/JSON 输出是官方推荐能力方向。

核心点4：工具=你未来的“系统接口”
今天是 inspect_slot / capture_evidence
未来就是：调用摄像头、调用机器人、写入Slot DB、触发事件、下发调度。

本周验收（做完就算过关）
输入：复核B12车位并取证
期望：模型先 get_slot_state(B12)，再 capture_evidence(B12, reason=...)，最后输出JSON总结。

输入：巡检A12车位
期望：至少调用 inspect_slot(A12)，输出包含 evidence/log id。
把 tools.py 里 B12 状态改成 Free
期望：模型策略变化（可能不取证，改成巡检/结束）。
