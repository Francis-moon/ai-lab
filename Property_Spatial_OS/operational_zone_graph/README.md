# operational_zone_graph(v4 OZG)

论文：Orchestrating Spatial Semantics via a Zone-Graph Paradigm for Intricate Indoor Scene Generation

Operational relation Graph = 空间对象 + 关系 + 状态 + 事件 + 任务 + 证据 + 执行反馈

V4 在 V3 operational_relation-graph 上增加一层 Zone as first-class operational container。

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

## 为什么有必要升级到 Zone-Graph

核心不是“房间生成”，而是三点：

从 object-centric 转向 zone-centric
ZoneMaestro 把复杂空间看成“功能容器的拓扑图”，不是连续真空里的对象堆叠。论文明确说，Zone-Graph 让模型把高层语义意图转成 functional zones 和 topological constraints。
先全局区域，再局部对象
论文把场景表示成 S = (D, G, T, A)：Zone Inventory、Intra-Zone Spatial Graph、Global Topology、Architecture。也就是先定义功能区，再定义区内对象关系，再定义区间拓扑，最后落到建筑边界。
Zone 可以吸收复杂度
论文里说 Zone-Graph 的 semantic encapsulation 可以隔离高密度依赖，避免长链生成中的语义漂移；实验证明 Zone-Graph SFT 相比无 Zone-Graph 版本减少过度堆叠和边界漂移。

宜泊的公共物业空间也有同类问题：
车位 / 通道 / 出入口 / 消防通道 / 电梯厅 / 设备房 / 充电区 / 装卸区 / 垃圾房 / 非机动车区
这些不是普通对象，而是运营区。不同区有不同：
状态
SLA
执行体
事件类型
摄像头覆盖
机器人可达性
风险权重
处置流程

所以 V4 的必要性是：
V3 解决“关系是否被验证”；
V4 解决“事件属于哪个运营区，区域之间如何影响调度与闭环”。

但是，论文目标是 3D indoor scene generation，宜泊目标是 property event operating system。

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

## V3 相比 V2 的核心变化

不是推翻 V2，而是在 V2 的 Scene Graph 基础上，把 state-aware 下沉到 Relation / Edge 层。

MomaGraph 的启发点正是：任务相关图不只是有节点和边，还要根据执行后的状态变化确认、削弱或剪枝关系边；论文里 knob 与 burner 的例子就是通过动作后的状态变化确认真实 control 边、剪掉错误边。
这和宜泊现在“事件状态机 + 调度内核 + 空间状态模型”的方向一致，但 V3 进一步把“状态感知”从 Event / Case / Task 下沉到 Scene Graph 的关系层。

V2：operational_scene_graph
V2 已经具备：
Event 状态
Case 生命周期
Task 状态
Outcome 回写
Feedback 修正
主要回答：
事件是什么？
Case 到哪一步？
任务派给谁？
执行结果是什么？
对象状态如何变化？

V3：operational_relation_graph
V3 让关系边也有生命周期：
hypothesis → confirmed / rejected / expired
例如：
event supports case
camera observes slot
robot verified case
case affects slot
executor assigned_to task
这些关系不再是静态配置，而是会被任务结果持续强化或削弱。

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

## V3 更适合以后做图推理

后面如果要做：
哪个摄像头误报高？
哪个车位异常高发？
哪个机器人复核最可靠？
哪个关系长期没有被验证？
哪个区域需要重新标定？
V3 就有数据基础。

V2 只能看 Case 和 Task。
V3 可以看“关系质量”。

## V4 相比 V3 的区别

V2 operational_scene-graph：Event / Case / Task 状态，事件处理到哪一步？
V3 operational_relation-graph：SceneEdge / Relation 状态，哪些关系被验证、削弱、拒绝？
V4 operational_zone-graph：FunctionalZone / ZoneTopology，哪个区域进入什么状态？区域关系如何影响调度？

V4 增加的是：
FunctionalZone
ZoneTopologyEdge
ZoneMember
Zone-aware Case
Zone-aware Scheduler
Zone Heat / Risk / SLA Policy

## 运行步骤

python -m app.seed
uvicorn app.main:app --reload
打开：
http://127.0.0.1:8000/docs
测试流程

1. 查看 Zone Graph

调用：
GET /zones
GET /zone-topology
GET /zone-members
你会看到：
zone:entrance-A
zone:lane-A-main
zone:parking-A
zone:equipment-A

以及：
entrance-A flow_to lane-A-main
lane-A-main adjacent_to parking-A
lane-A-main adjacent_to equipment-A

2. 停车区违停事件

调用：
{
  "event_id": "evt-701",
  "event_type": "illegal_parking_detected",
  "source": "ai_box",
  "source_node_id": "camera:A-cam-01",
  "target_node_id": "slot:A-003",
  "zone_id": "zone:parking-A",
  "confidence": 65
}
系统会：
创建 Case
读取 parking-A 的 zone policy
生成 remote_verify
更新 parking-A heat / state

3. 调度器运行

POST /scheduler/run
如果 parking-A 没有合适执行体，调度器会查相邻 Zone：
parking-A → lane-A-main
因此 robot-A-1 或 human-A-1 仍可接单。
这就是 Zone-Graph 的实际价值：
调度不是只看执行体类型，而是看执行体所在 Zone 与目标 Zone 的拓扑关系。

4. 查看区域上下文

GET /zones/zone:parking-A/context
返回：
zone
members
nodes
adjacent_zones
open_cases
open_tasks
这就是最小版 Case-relevant Zone Subgraph。

## V2核心点

1. Event Correlation 比 Dedup 更重要
Dedup 只解决重复报警。
Correlation 解决的是：
不同设备、不同时间、不同视角的事件，是否在支持同一个 Case。
这对宜泊非常关键，因为云岗亭、AI-BOX、机器人、人工作业本来就是多入口事件源。

2. Confidence Fusion 是降低误报的基础

AI-BOX 单帧告警不能直接变成强 Case。
机器人近距离复核、人工确认、云岗亭远程确认的权重应该不同。
所以系统应有：
source weight
+ evidence confidence
+ outcome feedback
而不是简单相信某一个算法输出。

3. Policy Engine 是产品化的关键

不要长期把业务规则写死在 if-else 里。
第一阶段可以用 Python dict。
第二阶段应进入数据库配置。
第三阶段再做可视化规则台。
最终形态：
case_type + task_type + outcome_type → next_state + next_task + SLA + fallback
这是宜泊未来“可复制交付”的关键。

4. SLA Engine 决定客户是否感知价值

客户不只关心系统是否发现异常。
客户更关心：
多久响应？
有没有超时？
谁处理？
是否复核？
是否闭环？
没有 SLA 引擎，系统很难从“告警平台”升级为“运营平台”。

5. Feedback Engine 决定系统能否变准

Operational Twin 不是一次性建成的。
它靠真实处置结果持续校正：
误报 → 调低规则权重
地图错 → 生成 Map Patch
摄像头盲区 → 标记 blindspot
重复事件 → 优化 correlation
SLA 超时 → 优化调度策略
这就是“越跑越懂场”的壁垒。

6. Map Patch 是轻量地图进化机制

不要一开始追求完美地图。
应该允许系统在运营中产生 patch：
摄像头盲区
车位边界错误
通道关系错误
机器人不可达点
高风险区域
地图不是画出来的，是运营出来的。

7. Risk Profile 是从单事件走向区域运营

当你积累足够反馈后，系统就可以回答：
哪个车位最常误报？
哪个通道最常堵？
哪个摄像头最不可靠？
哪个区域最容易超 SLA？
哪个执行体最容易失败？
这比单个 Case 更有经营价值。

8. 下一步研发路线

V2：现在这版
Operational Scene Graph
+ Case Engine
+ Dynamic Policy
+ SLA
+ Feedback
+ Map Patch
目标：跑通单项目闭环。

### 产品化版

规则配置后台
人工审核台
证据链管理
项目级指标看板
多项目模板复制
目标：可交付给真实物业项目。

### 平台化版

图数据库 Neo4j / NebulaGraph
PostGIS 空间查询
Kafka / Redis Stream 事件流
策略 A/B Test
跨项目规则迁移
调度仿真

目标：形成宜泊自己的 property event operating system

## V3 核心点

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

## V4 核心点

1. Zone 不再只是普通 SceneNode
在 V3 中，zone:A 更像一个节点。
在 V4 中，Zone 是运营容器：
状态
热度
风险
容量
占用
SLA policy
边界
成员对象
邻接拓扑
这是质变。

2. 调度开始 Zone-aware
V3 调度主要是：
task type + executor type + executor status
V4 调度变成：
task zone
+ zone heat
+ zone policy
+ executor zone
+ adjacent zone topology
+ SLA
这更接近真实物业调度。

3. Zone 抑制图爆炸
你之前担心 node 太多太细。
Zone-Graph 正好解决这个问题。
不是让所有对象都进入全局推理，而是：
先找 Zone
再取 Zone context
再取相关对象
再生成任务
也就是：
全图 → 区域子图 → Case 子图

4. 宜泊的公共空间天然是 Zone-first
物业客户不关心“某个 bounding box”。
他们关心：
入口是否堵？
消防通道是否被占？
电梯厅是否异常停留？
设备房是否故障？
装卸区是否被占用？
非机动车区是否溢出？
这些都是 Zone-level 状态。

5. V4 是必要升级，但不是最高优先级全部重构
建议研发节奏：
V3 保留：关系状态、证据、Case Engine
V4 增加：FunctionalZone、ZoneTopology、Zone-aware Scheduler
不要重写：不要做生成式 ZoneMaestro / Z-GRPO

## 最终判断

如果宜泊只做停车场违停/设备告警，V3 足够。
如果宜泊要进入物业公共空间，V4 有必要。
原因很简单：
物业公共空间不是“对象集合”，而是“功能区域集合”。
运营动作不是围绕单个检测框，而是围绕区域状态、区域拓扑、区域 SLA 和区域执行资源。
所以 V4 operational_zone-graph 是合理升级。
但它必须是轻量运营 Zone-Graph，不是论文里的完整生成式 3D Zone-Graph。

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
