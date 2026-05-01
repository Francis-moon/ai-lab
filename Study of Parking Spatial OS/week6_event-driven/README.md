# 🎯这一周的目标，是把你前面学的“对象、状态、任务”真正串起来

事件 → 状态更新 → 生成任务 → 执行任务 → 写入结果

这正是战略里最关键的那条链路：空间对象 + 状态机 + 事件驱动 + 任务编排，也是 Parking Spatial OS 的核心骨架。
文档里反复强调“对象-事件-任务-结果”的闭环数据资产，这一周就是在手工做一个最小闭环原型。

这周学完你要真正理解的3件事：

1. 事件不是“消息”，而是“业务变化的触发器”
例如：
发现违停 IllegalParking
发现车位被占 SlotOccupied
复核完成 Rechecked
证据采集完成 EvidenceCaptured

2. 任务不是“机器人自己想做什么”，而是“系统针对对象下发的动作”
例如：
-Inspect(slot_id)
-CaptureEvidence(slot_id)
-NotifySecurity(slot_id)

3. 闭环的关键不是识别，而是结果回写
如果只有识别，没有：
-状态更新
-任务生成
-执行结果
-历史记录
那就不是系统，只是一个“会报警的小工具”。

🧪练习
练习1：自己新增一个事件类型
例如：
DIRTY_SLOT = "DirtySlot"
要求：
触发后状态改成 CHECKING
自动生成 INSPECT
执行后生成 CLEARED
**Finished** -> INSPECT后注意生成RECHECK，RECHECK来发出CLEARED，最终状态才改为RESOLVED

练习2：给任务加优先级
在 Task 里加字段：
priority: int = 1
然后让：
NOTIFY_SECURITY 优先级最高
CAPTURE_EVIDENCE 第二
RECHECK 第三
再在 process_tasks() 前先排序。
**Finished** -> 已实现 Task.priority，并在 process_tasks() 前按优先级排序；当前顺序为 NOTIFY_SECURITY > CAPTURE_EVIDENCE > RECHECK > INSPECT。

练习3：同一车位重复违停，避免重复派任务:
目标：
如果 Slot-A01 已经是 ILLEGAL，再次收到 IllegalParking，不要重复生成完全相同的任务。
这会逼你开始思考：
去重
幂等
状态保护
这就是系统工程的核心味道了。
**Finished** -> 已实现状态保护：当车位已经是 ILLEGAL 时，再收到 IllegalParking 会直接忽略，增加了模拟任务3，验证成功。

练习4：增加 Zone 概念的影响
例如：
Zone-A 是高优先级区域
Zone-B 是普通区域
让高优先级区域出现事件时，任务优先级自动更高。
这一步会让你开始从“单点功能”走向“空间系统”。
**Finished** -> 已实现 Zone 权重：Zone-A 的任务优先级会高于 Zone-B，任务排序时会先按 Zone，再按任务类型优先级。

练习5：增加循环条件：只要事件队列或任务队列还有内容，就继续执行，直到结束
**Finished** -> 在 parking_system.py 新增了 run_until_idle(max_rounds=50)
循环条件：只要事件队列或任务队列还有内容，就继续执行
每轮自动执行：先 process_events()，再 process_tasks()
增加保险：max_rounds 防止异常规则导致死循环
结束时会打印“共执行了多少轮”
