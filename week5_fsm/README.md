🎯目标
把战略里强调的“状态机与事件系统”先做出来，避免系统陷入 if-else 泥潭。

第5周核心点（你必须吃透）
1）为什么要状态机
把“车位/通道/设备”的业务生命周期显式化：
允许哪些状态（State）
允许哪些事件触发迁移（Event/Trigger）
迁移时做什么动作（Action/Callback）
这正对应你们 Parking Spatial OS 的“状态机与事件系统”部分：事件必须触发策略、改变任务、进入业务系统。

2）本周只做最小闭环
只做一个对象：Slot（车位）
只做4个状态：FREE / OCCUPIED / ILLEGAL / CLEARED
只做5个事件：occupy / detect_illegal / clear / release / reset
注意：CLEARED 是“已处理待复核”的中间态（贴合“取证/处置/复核”的闭环语义），不是终态。

3）工程纪律（避免未来烂尾）
任何状态变化必须写入 history（审计/追溯）
不允许绕开状态机直接改 state
事件要能被外部系统（后续FastAPI/Agent）调用

🧪 本周你必须完成的练习（照做即可）
练习1：加一个事件 LaneBlocked（模拟通道堵塞）
做法：
在 STATES 不变的情况下，新增一个对象 Lane（可以复制 Slot 的结构）
Lane 的状态做 3 个：CLEAR / BLOCKED / CLEARED
事件：block / clear / release / reset
跑 demo
意义：对应你们文档里的典型事件 LaneBlocked。
**Finished**

练习2：把“clear”拆成两步（更贴近闭环）
把 ILLEGAL -> CLEARED 改成：
ILLEGAL -> CLEARED（取证完成）
CLEARED -> FREE（复核通过）
已经在模板里实现了这个语义（clear/release）。你要做的是：
在 clear 时强制 evidence 必填；没 evidence 就 raise ValueError
**Finished, and ts change to china timezone**

练习3：把 history 输出成 JSON 文件
新增 export_history(slot_id).json：
文件名：history_A-23.json
内容：history 列表（ts/event/from/to/note）
**Finished, only SLOT no LANE**

这周做完，你在“Spatial OS”里对应掌握了什么
你将掌握战略文档中 Parking Spatial OS 的一根主梁：
“状态机 + 事件驱动”（避免 if-else、让事件可触发策略/任务/进入业务系统）。
后续第6周的“事件循环”，第10周的“LangGraph Agent”，都直接复用这套结构。
