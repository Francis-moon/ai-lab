# Operational Twin 的本质是“可回放的运营状态系统”

事件不能无限新增，要去重/合并
区域不是静态地图，而是有状态机
任务不是单步，而是任务链
每一步都要有审计日志

## 运行步骤
python -m app.seed
uvicorn app.main:app --reload
打开：
http://127.0.0.1:8000/docs

## 必须完成的练习

练习1：处理一个违停事件
调用：
{
  "event_id": "evt-301",
  "event_type": "illegal_parking_detected",
  "slot_id": "A-003",
  "zone": "A",
  "source": "ai_box"
}
预期生成 3 步任务链：
remote_verify
recheck_slot
capture_evidence

练习2：验证事件去重/合并
5分钟内再发：
{
  "event_id": "evt-302",
  "event_type": "illegal_parking_detected",
  "slot_id": "A-003",
  "zone": "A",
  "source": "robot"
}
预期返回：
{
  "status": "merged",
  "merged_into": "evt-301"
}
这说明系统不会因多设备重复报警而制造多个工单。

练习3：运行调度器
调用：
POST /scheduler/run
预期：
第一步 remote_verify 会分配给 cloud-A-1。

练习4：完成第一步任务
调用：
POST /tasks/evt-301-01-remote-verify/complete
然后再次运行：
POST /scheduler/run
预期：
第二步 recheck_slot 才会被调度。
这验证了：
多步骤任务链不是并发乱派，而是有依赖顺序。

练习5：查看区域状态变化
调用：
GET /zones
你会看到 A 区：
active_event_count 上升
heat 上升
status 可能从 normal 变成 warning 或 high_risk

练习6：查看回放审计
调用：
GET /audit
或：
GET /replay/event/evt-301
你会看到：
event_created
zone_state_updated
task_chain_created
event_processed_by_agent
这就是 Operational Twin 的“可回放”基础。

## 本周核心点

### 核心点1：事件去重是统一事件引擎的第一道门

真实物业场景里，一个异常可能同时被：
AI-BOX
摄像头
机器人
人工
云岗亭
重复发现。
如果不去重，系统会制造大量伪工单，反而增加运营负担。
所以第12周第一件事就是：
同一对象、同一类型、同一区域、短时间内，只形成一个主事件。

### 核心点2：区域状态机比单点告警更有战略价值

第11周你已经有了 zone_heat。
第12周进一步变成：
normal → warning → high_risk → blocked
这意味着系统从：
“某个相机报了警”
升级为：
“A区进入高风险运营状态”
这就是从告警系统走向空间状态模型。

### 核心点3：任务链才接近真实运营

真实处置不是一步完成。
违停事件可能是：
远程确认 → 机器人复核 → 取证 → 人工处置 → 关闭
通道堵塞可能是：
人工清障 → 机器人复核 → 状态恢复
所以任务链比单任务更贴近真实业务。

### 核心点4：Audit Log 是 Operational Twin 的底座

没有审计日志，系统只是“当前状态”。
有了审计日志，系统才变成：
可追溯、可复盘、可考核、可优化的运营系统。
这也是未来对物业客户最有价值的部分：
谁发现的？
谁处理的？
多久响应？
是否超 SLA？
是否误报？
是否重复？
是否复核？

### 核心点5：Operational Twin 不是 3D 大屏

宜泊不应优先做重型 3D Twin。
真正有价值的是：
事件、区域、任务、执行体、结果之间的持续状态关系。
也就是你现在这套最小内核：
Event → ZoneState → TaskChain → Executor → AuditLog
这才是“运营孪生”，不是“展示孪生”。

## 验收标准

你跑通以下 7 条，就算完成三个月训练：
能处理一个事件
能自动去重/合并重复事件
能更新区域状态
能生成多步骤任务链
能按依赖顺序调度任务
能完成任务并释放执行体
能通过 audit/replay 复盘完整过程
