# state_aware_operational_graph(v3 SAOG)

Operational Scene Graph = 空间对象 + 关系 + 状态 + 事件 + 任务 + 证据 + 执行反馈

## 正确定位

宜泊应该做的不是普通 Scene Graph，而是：

Operational Scene Graph
= Spatial Scene Graph
+ Event Graph
+ Case Graph
+ Task Graph
+ Evidence Graph
+ Executor Graph

也就是：
空间对象图：Zone / Lane / Slot / Camera / Entrance / Robot / Vehicle
事件关系图：Event 发生在哪个对象上，由哪个设备发现
Case状态图：某个异常 Case 当前处于 suspected / verifying / confirmed / closed
任务执行图：Task 派给谁、依赖谁、是否完成
证据链图：图片、视频、人工备注、机器人复核结果
反馈学习图：误报、漏报、规则错误、地图错误
核心不是 3D 可视化，而是运营可推理。

## 新架构：Scene Graph + Case Engine

之前建议从 Task Chain 升级为 Case Engine。现在再进一步：
Event Ingestion
    ↓
Operational Scene Graph
    ↓
Case Engine
    ↓
Decision Gateway
    ↓
Task Scheduler
    ↓
Outcome Feedback
    ↓
Graph Update + Audit Replay
换句话说：
Scene Graph 是空间记忆层；Case Engine 是运营状态机；Scheduler 是执行调度层。
三者不能混在一起。

不是推翻 V2，而是在 V2 的 Scene Graph 基础上，把 state-aware 下沉到 Relation / Edge 层。

MomaGraph 的启发点正是：任务相关图不只是有节点和边，还要根据执行后的状态变化确认、削弱或剪枝关系边；论文里 knob 与 burner 的例子就是通过动作后的状态变化确认真实 control 边、剪掉错误边。
这和宜泊现在“事件状态机 + 调度内核 + 空间状态模型”的方向一致，但 V3 进一步把“状态感知”从 Event / Case / Task 下沉到 Scene Graph 的关系层。

## V3 相比 V2 的核心变化

V2：operational_scene_graph
主要回答：
事件是什么？
Case 到哪一步？
任务派给谁？
执行结果是什么？
对象状态如何变化？

V3：state_aware_operational_graph
进一步回答：
哪些空间关系被验证了？
哪些功能关系被削弱了？
哪些边是疑似关系？
哪些边因误报被剪枝？
哪些关系会影响下一步调度？

也就是从：
Case-aware / Task-aware
升级到：
Relation-aware / Edge-aware

## 运行步骤

python -m app.seed
uvicorn app.main:app --reload
打开：
http://127.0.0.1:8000/docs
测试流程

1. 查看初始 Scene Graph
调用：
GET /scene/nodes
GET /scene/edges
你会看到：
zone:A
lane:A-main
slot:A-003
camera:A-cam-01
robot:robot-A-1
以及关系：
zone contains lane
lane near slot
camera observes slot
robot operates_in zone

2. 摄像头发现疑似违停
调用：
POST /events/ingest
{
  "event_id": "evt-401",
  "event_type": "illegal_parking_detected",
  "source": "ai_box",
  "source_node_id": "camera:A-cam-01",
  "target_node_id": "slot:A-003",
  "zone": "A",
  "confidence": 65
}
预期
系统创建：
Event node
Case node
remote_verify task
Event → Case
Case → Task

3. 调度任务
调用：
POST /scheduler/run
预期：
remote_verify 被分配给 cloud-A-1。

4. 提交任务结果：低置信度
调用：
POST /tasks/outcome
{
  "outcome_id": "out-401-1",
  "task_id": "你实际生成的remote_verify任务ID",
  "outcome_type": "low_confidence",
  "confidence": 60,
  "note": "画面模糊，需要机器人近距离复核",
  "created_by": "cloud_operator"
}
预期：
系统不会关闭 Case，而是动态生成：
robot_recheck
这验证了你刚才提出的关键点：
同一个事件，任务1结果不同，任务2不同。

5. 提交任务结果：机器人确认仍存在
调度后，再提交POST /tasks/outcome：
{
  "outcome_id": "out-401-2",
  "task_id": "robot_recheck任务ID",
  "outcome_type": "still_present",
  "confidence": 92,
  "evidence_url": "mock://robot-image-001.jpg",
  "note": "机器人确认车辆仍占用异常位置",
  "created_by": "robot"
}
预期：
系统生成：
capture_evidence
同时 Scene Graph 中会出现 evidence node。

6. 如果一开始远程确认是误报
对另一个事件测试：

{
  "outcome_type": "false_alarm",
  "confidence": 90
}
预期：
系统直接关闭 Case，不会生成机器人复核任务。

## V2测试

1. 事件关联测试
先发一个 AI-BOX 事件：
{
  "event_id": "evt-501",
  "event_type": "illegal_parking_detected",
  "source": "ai_box",
  "source_node_id": "camera:A-cam-01",
  "target_node_id": "slot:A-003",
  "zone": "A",
  "confidence": 65
}
再发一个机器人复核事件：
{
  "event_id": "evt-502",
  "event_type": "illegal_parking_detected",
  "source": "robot",
  "source_node_id": "robot:robot-A-1",
  "target_node_id": "slot:A-003",
  "zone": "A",
  "confidence": 92
}
预期：
evt-502 不新建 Case
而是 correlated 到 evt-501 创建的 Case
Case confidence 上升

2. SLA 测试
把某个任务的 sla_minutes 改成很小，例如 0 或 1。
等待后调用：
POST /sla/check
预期：
任务 priority 变 critical
Case state 变 escalated
生成 SLA violation

3. 反馈测试
关闭一个 Case 后提交：
{
  "feedback_id": "fb-001",
  "case_id": "case-evt-501",
  "task_id": null,
  "feedback_type": "false_positive",
  "root_cause": "camera_angle",
  "note": "摄像头角度导致误判",
  "created_by": "operator",
  "attrs": {
    "camera_id": "camera:A-cam-01"
  }
}
预期：
生成 feedback
更新 risk_profile
如果是 map_error / camera_blindspot，会生成 map_patch

4. 地图 patch 测试
提交：
{
  "patch_id": "patch-test-001",
  "target_node_id": "camera:A-cam-01",
  "patch_type": "mark_blindspot",
  "payload": {
    "note": "摄像头被柱子遮挡"
  },
  "source_case_id": "case-evt-501",
  "proposed_by": "operator"
}
然后调用：
POST /map-patches/patch-test-001/apply
预期：
camera:A-cam-01 的 attrs 增加 blindspot=true

## 核心点

### Scene Graph 是 Operational Twin 的“空间记忆”

以前你只有表：
Event / Task / Executor
现在你有图：
Camera observes Slot
Event happens_on Slot
Event creates Case
Case requires Task
Task produces Evidence
Robot operates_in Zone
这让系统不只是存数据，而是能推理关系。

### 3D Scene Graph 不等于 3D 大屏

宜泊最不应该做的是：
先做漂亮3D展示
最应该做的是：
先做运营图谱

也就是：
对象在哪里
谁观察它
谁影响它
出了什么事
谁处理
证据是什么
最后状态如何
这比可视化重要得多。

### Case Engine 是 Scene Graph 的“动态状态机”

Scene Graph 负责表达：
空间和关系
Case Engine 负责表达：
业务状态变化
例如：
suspected → verifying → confirmed → waiting → closed
不要把这两个系统混淆。

### 任务不是链，而是由 Outcome 驱动

正确逻辑：
Task Outcome → Decision Gateway → Next Task / Close Case / Escalate
而不是：
Task1 → Task2 → Task3
这是从工单系统升级为运营系统的关键。

### 宜泊应该优先做 2.5D Operational Scene Graph

不建议一开始做重型 3D Scene Graph。
第一阶段应该是：
Zone / Lane / Slot / Camera / Robot / Entrance
+ x, y, floor
+ optional z
+ relation
+ state
也就是 2.5D Operational Scene Graph。

因为宜泊的商业目标不是科研，而是：
降误报
提闭环率
降人工巡检
提 SLA
可复制交付

## V2核心点

### Event Correlation 比 Dedup 更重要

Dedup 只解决重复报警。
Correlation 解决的是：
不同设备、不同时间、不同视角的事件，是否在支持同一个 Case。
这对宜泊非常关键，因为云岗亭、AI-BOX、机器人、人工作业本来就是多入口事件源。

### Confidence Fusion 是降低误报的基础

AI-BOX 单帧告警不能直接变成强 Case。
机器人近距离复核、人工确认、云岗亭远程确认的权重应该不同。
所以系统应有：
source weight
+ evidence confidence
+ outcome feedback
而不是简单相信某一个算法输出。

### Policy Engine 是产品化的关键

不要长期把业务规则写死在 if-else 里。
第一阶段可以用 Python dict。
第二阶段应进入数据库配置。
第三阶段再做可视化规则台。
最终形态：
case_type + task_type + outcome_type → next_state + next_task + SLA + fallback
这是宜泊未来“可复制交付”的关键。

### SLA Engine 决定客户是否感知价值

客户不只关心系统是否发现异常。
客户更关心：
多久响应？
有没有超时？
谁处理？
是否复核？
是否闭环？
没有 SLA 引擎，系统很难从“告警平台”升级为“运营平台”。

### Feedback Engine 决定系统能否变准

Operational Twin 不是一次性建成的。
它靠真实处置结果持续校正：
误报 → 调低规则权重
地图错 → 生成 Map Patch
摄像头盲区 → 标记 blindspot
重复事件 → 优化 correlation
SLA 超时 → 优化调度策略
这就是“越跑越懂场”的壁垒。

### Map Patch 是轻量地图进化机制

不要一开始追求完美地图。
应该允许系统在运营中产生 patch：
摄像头盲区
车位边界错误
通道关系错误
机器人不可达点
高风险区域
地图不是画出来的，是运营出来的。

### Risk Profile 是从单事件走向区域运营

当你积累足够反馈后，系统就可以回答：
哪个车位最常误报？
哪个通道最常堵？
哪个摄像头最不可靠？
哪个区域最容易超 SLA？
哪个执行体最容易失败？
这比单个 Case 更有经营价值。

## 下一步研发路线

V2：现在这版
Operational Scene Graph
+ Case Engine
+ Dynamic Policy
+ SLA
+ Feedback
+ Map Patch
目标：跑通单项目闭环。

V3：产品化版
规则配置后台
人工审核台
证据链管理
项目级指标看板
多项目模板复制
目标：可交付给真实物业项目。

V4：平台化版
图数据库 Neo4j / NebulaGraph
PostGIS 空间查询
Kafka / Redis Stream 事件流
策略 A/B Test
跨项目规则迁移
调度仿真

目标：形成宜泊自己的 property event operating system

## 宜泊真正的壁垒

不是“更会看”，而是看见异常：
→ 理解空间对象
→ 关联 Case
→ 动态派任务
→ SLA 约束
→ 证据闭环
→ 反馈校正
→ 跨项目复用

这才是 Operational Scene Graph 的商业价值
