# Spatial OS / Orchestration Layer 的最小版本

多执行体调度
任务完成自动释放执行体
机器人低电量自动生成充电任务
fallback 机制
引入区域热度（heat）
引入 SLA / 超时优先级
更贴近宜泊的任务路由逻辑

这已经非常接近你们文档里强调的
统一事件引擎 + 调度中枢 + 闭环系统 了。你们战略里明确把核心放在“事件状态机 + 调度内核 + 空间状态模型”，而不是单点 AI 模型，这一版正是在做那个“调度内核”的最小原型

## 只解决 5 件事

1,任务不是生成就结束，而是要被分配和执行
2,执行体是资源池，不是写死的名字
3,调度要考虑优先级、SLA、热度、可用性、电量
4,失败时必须有 fallback
5,机器人不是永远可用，低电量要自动去充电

你做完这周，会真正理解：
真正难的不是“发现异常”，而是“谁来处理、何时处理、处理失败怎么办”

运行步骤
第一步：初始化数据
python -m app.seed
第二步：启动服务
uvicorn app.main:app --reload
第三步：打开文档
http://127.0.0.1:8000/docs

## 按顺序完成的练习

练习1：检查初始资源池
调用：
GET /executors
GET /zones
你会看到：
robot-A-1 电量 80
robot-B-1 电量 15
A 区 heat 高于 B 区

练习2：创建并处理一个 A 区违停事件
调用：
POST /agent/process-event
{
  "event_id": "evt-201",
  "event_type": "illegal_parking_detected",
  "slot_id": "A-003",
  "zone": "A",
  "source": "ai_box"
}
然后看：
GET /tasks
会生成一个任务，优先级较高，SLA 更短。

练习3：运行调度器
调用：
POST /scheduler/run
预期：
A 区违停任务会优先被分给 robot-A-1
因为：
heat 高
SLA 紧
robot-A-1 空闲且电量够

练习4：完成任务，自动释放执行体
调用：
POST /tasks/{task_id}/complete
例如：
evt-201-inspect
预期：
task 变成 done
robot-A-1 自动释放
robot-A-1.status = idle
电量会下降 10

这一步验证了：
任务完成自动释放执行体

练习5：验证低电量机器人自动充电任务
B 区机器人初始电量是 15。
调用：
POST /scheduler/run
预期：
系统会自动为 robot-B-1 创建 charge_robot 任务

查看：
GET /tasks
你会看到一个 charge-robot-B-1 的任务。

练习6：让低电量机器人执行充电任务
再调一次：
POST /scheduler/run
若该机器人空闲且支持 charge_robot，就会接单进入 charging。
之后执行：
POST /tasks/charge-robot-B-1/complete

预期：
电量回到 100
状态回到 idle

这一步验证了：
机器人低电量自动充电任务

练习7：验证 fallback 机制
先造一个任务：
{
  "task_id": "manual-test-001",
  "task_type": "inspect_illegal_parking",
  "slot_id": "A-001",
  "zone": "A",
  "preferred_assignee": "robot",
  "priority": "high",
  "sla_minutes": 5,
  "zone_heat": 8,
  "fallback_chain": "robot,human,cloud_operator"
}
运行调度器，让它先分给 robot。
再调用：
POST /tasks/manual-test-001/fail

预期：
老执行体释放
任务重新回到 created
scheduler 自动重新分配
若 robot 不合适，则 fallback 给 human 或 cloud_operator
这一步验证了：
fallback 机制

练习8：验证 SLA + 热度影响调度顺序
手动再创建两个任务：
任务A：
{
  "task_id": "task-high-heat",
  "task_type": "inspect_illegal_parking",
  "slot_id": "A-001",
  "zone": "A",
  "preferred_assignee": "robot",
  "priority": "medium",
  "sla_minutes": 5,
  "zone_heat": 8,
  "fallback_chain": "robot,human,cloud_operator"
}

任务B：
{
  "task_id": "task-low-heat",
  "task_type": "inspect_illegal_parking",
  "slot_id": "B-001",
  "zone": "B",
  "preferred_assignee": "robot",
  "priority": "medium",
  "sla_minutes": 20,
  "zone_heat": 2,
  "fallback_chain": "robot,human,cloud_operator"
}

运行：
POST /scheduler/run
预期：
task-high-heat 会更早被调度
因为 score 由：
priority
zone_heat
sla_minutes
共同决定。

## 核心点

下面这部分比代码更重要。
核心点1：调度器的本质不是“分任务”，而是“管理资源冲突”
多执行体调度，不是简单找个人做事，而是处理：
谁空闲
谁合适
谁更近
谁电量够
谁技能匹配
谁失败后能兜底
这就是你们未来 orchestration layer 的雏形。

核心点2：执行体必须是“资源池”
这里你已经从“写死 robot/human 字符串”升级成了：
Executor 表
status
battery_level
current_task_id
can_handle
这意味着：
执行体变成了可调度资源，而不是写死逻辑。
这一步非常关键。

核心点3：任务完成自动释放执行体，是闭环系统的基础
如果没有自动释放，系统很快会“资源泄漏”。
真实系统里最常见的问题不是 AI 不聪明，而是：
任务完成了但资源没释放
资源忙闲状态脏了
调度器误判资源不可用
所以这句逻辑虽然简单，但极重要：
executor.current_task_id = None
executor.status = "idle"
核心点4：低电量自动充电，是机器人系统和人工系统最大的区别
人类不会因为电量不足退出系统，机器人会。
因此机器人调度一定要多一层：
battery state
charging state
charge task
这就是为什么机器人调度比人工工单系统复杂得多。

核心点5：fallback 不是补丁，而是调度系统的刚需
真实物业系统里，失败是常态：
机器人离线
人工没接单
云岗亭无法远程确认
任务执行失败
所以系统不是“有没有 fallback”，而是：
fallback 是默认设计，不是例外。

核心点6：热度和 SLA 让系统从“静态派单”升级为“动态优先级系统”
你现在有了两种很关键的维度：
1. 区域热度 zone_heat
表示这个区域当前更值得调度资源。

2. SLA sla_minutes
表示这个任务更急。
这意味着系统已经不再是：
谁先来谁先做
而是开始变成：
谁更重要谁先做
这一步是从工单系统走向运行系统的关键。

核心点7：Agent 负责生成任务，Scheduler 负责分配任务
这两个必须分层。
Agent 的职责
理解事件
生成任务
设定任务属性
Scheduler 的职责
找合适执行体
决定谁来做
管理忙闲状态
处理失败重调度
如果这两层不分开，后面系统一定会越来越乱。

九、这一版和宜泊场景的对应关系
你们现在真实最值得做的，并不是单点炫技，而是：
云岗亭 / AI-BOX / 机器人 / 人工
都进入统一事件和任务系统
然后由调度内核决定谁去处理
你们文档里已经明确提出，最关键的壁垒是：
统一事件引擎
空间状态模型
调度与闭环系统
低成本感知融合
持续校正系统

这一版代码已经很接近最小闭环：
Event = 异常输入
Task = 任务输出
Executor = 资源池
Scheduler = 调度内核
ZoneState = 简易空间状态
Complete/Fail = 闭环反馈
也就是你们想做的
Operational Twin 最小内核。

## 你本周完成后的验收标准

下面 7 条成立，这周就算过关：
你能生成事件并通过 Agent 生成任务
你能运行 scheduler 分配任务
任务能分配给 robot / human / cloud_operator
任务完成后执行体会自动释放
机器人低电量会自动触发充电任务
任务失败时能走 fallback 重调度
你理解 heat + SLA 为什么影响调度顺序

## 这版的局限

我直接指出来，避免你误判。
1. 还没有真实时间流逝
现在 SLA 只是任务属性，还没有真正做超时计时器。

2. 还没有多机器人冲突消解
还没有路径冲突、区域占用冲突。

3. 还没有跨区域调度
当前只做同区优先，没有做跨区借调。

4. 还没有任务链
比如“先复核，再驱离，再验收”。
但作为第11周，这版已经足够好。

## 下一步最值得升级的方向

下一周最应该加 4 个能力：

1. 任务状态机
created -> assigned -> in_progress -> done / failed

2. 事件去重与合并
同一区域重复报警合并成一个事件簇

3. 区域状态机
normal / congested / blocked / high_risk

4. 多机器人冲突与路径资源锁
让两个机器人不能同时占用同一区域资源
