# Operational Scene Graph = 空间对象 + 关系 + 状态 + 事件 + 任务 + 证据 + 执行反馈

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

预期：

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

调度后，再提交：

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

六、核心点
1. Scene Graph 是 Operational Twin 的“空间记忆”

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

2. 3D Scene Graph 不等于 3D 大屏

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

3. Case Engine 是 Scene Graph 的“动态状态机”

Scene Graph 负责表达：

空间和关系

Case Engine 负责表达：

业务状态变化

例如：

suspected → verifying → confirmed → waiting → closed

不要把这两个系统混淆。

4. 任务不是链，而是由 Outcome 驱动

正确逻辑：

Task Outcome → Decision Gateway → Next Task / Close Case / Escalate

而不是：

Task1 → Task2 → Task3

这是从工单系统升级为运营系统的关键。

5. 宜泊应该优先做 2.5D Operational Scene Graph

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