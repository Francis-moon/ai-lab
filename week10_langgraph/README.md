# 可调用 API 的任务型 Agent

事件 → 判断 → 生成任务 → 调用接口 → 更新状态 → 返回结果
Unified Event Engine + Task Orchestration 的最小雏形了。

## 第10周到底学什么

只学 4 件事：
什么是 Agent 工作流，不是普通聊天
什么是 State
什么是 Tool/API 调用
什么是 事件驱动任务闭环

本周做完，你会真正理解：
LLM 不是核心
API 不是核心
状态机 + 工具调用 + 任务闭环 才是核心

## 运行

第一步：初始化数据库
python -m app.seed
第二步：启动服务
uvicorn app.main:app --reload
第三步：打开文档
浏览器访问：
http://127.0.0.1:8000/docs

## 做练习

第一步：初始化测试数据
在项目根目录执行：
python -m app.seed
你会看到：
Seed data inserted successfully.

第二步：启动服务
uvicorn app.main:app --reload
正常会看到：
Uvicorn running on http://127.0.0.1:8000

第三步：打开接口文档
浏览器访问：
http://127.0.0.1:8000/docs

练习1：先验证 Slot API 正常
测试：
GET /slots
GET /slots/A-003
你应该能看到 A-003 当前状态是 illegal。

练习2：创建一个事件
在 /docs 中调用：
POST /events
Body：
{
  "event_id": "evt-001",
  "event_type": "illegal_parking_detected",
  "slot_id": "A-003",
  "zone": "A",
  "source": "ai_box"
}
然后再看：
GET /events

练习3：直接让 Agent 处理事件
调用：
POST /agent/process-event
Body：
{
  "event_id": "evt-002",
  "event_type": "illegal_parking_detected",
  "slot_id": "A-003",
  "zone": "A",
  "source": "ai_box"
}

你应该看到类似返回：

{
  "event_id": "evt-002",
  "decision": "create_inspection_task",
  "task_result": {
    "id": 1,
    "task_id": "inspect_illegal_parking-A-003",
    "task_type": "inspect_illegal_parking",
    "slot_id": "A-003",
    "zone": "A",
    "assignee": "robot",
    "priority": "high",
    "status": "created"
  },
  "slot_update_result": null,
  "status": "success"
}

练习4：查看 Task 是否真的生成
调用：
GET /tasks
你应该看到一条任务。

练习5：测试“先改状态再建任务”
准备一个本来不是 illegal 的车位，比如 B-003。
调用：
{
  "event_id": "evt-003",
  "event_type": "illegal_parking_detected",
  "slot_id": "B-003",
  "zone": "B",
  "source": "robot"
}

预期结果：
Agent 发现当前不是 illegal
先调用 Slot API 改成 illegal
再创建巡检任务

练习6：测试“通道堵塞事件”
调用：
{
  "event_id": "evt-004",
  "event_type": "lane_blocked_detected",
  "slot_id": "B-002",
  "zone": "B",
  "source": "ai_box"
}
预期结果：
创建一个 clear_blocked_lane 任务
assignee 是 human

练习7：测试“释放车位事件”
调用：
{
  "event_id": "evt-005",
  "event_type": "slot_freed_detected",
  "slot_id": "A-002",
  "zone": "A",
  "source": "camera"
}
预期结果：
Agent 更新 slot 状态为 free
不一定创建任务

## 这版为什么“更贴近宜泊场景”

你们未来最有价值的，不是“一个会说话的 Agent”，而是：
把事件源统一进系统，然后自动路由为任务，再形成闭环
这正是你们文档里反复强调的方向：
统一事件引擎、空间状态模型、调度与闭环系统、把异常转成任务和验收结果
这个模板已经对应了最小闭环：
输入层：Event
空间对象：Slot
调度输出：Task
Agent：决策与调用工具
闭环：事件 processed、任务 created、状态 updated
这就是极简版 Operational Twin kernel。

## 核心点

下面这部分比代码更重要。

### 核心点1：LangGraph 的本质不是“大模型框架”，而是“状态图框架”

记住：
Prompt 只是表面
Workflow 才是骨架
在这段代码里，真正重要的是：
load_context -> decide_action -> execute_action -> finalize
这才是 Agent 的本体。

### 核心点2：State 才是 Agent 的记忆

这里的 AgentState 很关键：
class AgentState(TypedDict):
    event_id: str
    event_type: str
    slot_id: Optional[str]
    zone: str
    source: str
    current_slot_state: Optional[str]
    decision: Optional[str]
    task_result: Optional[dict]
    slot_update_result: Optional[dict]
    final_result: Optional[dict]
    error: Optional[str]
这说明 Agent 不是一次性问答，而是在流程中不断积累状态。
未来你们真正的空间智能系统，本质上也是大 State：
当前区域状态
当前事件状态
当前任务状态
当前执行体状态

### 核心点3：Tool 不一定非要是“大模型 function calling”

你现在这版里，Tool 本质上是：
get_slot
update_slot_state
create_task
mark_event_processed

这些工具是通过 HTTP API 实现的。
这比把所有逻辑写死在 Agent 里更对。
因为未来系统一定是：
Agent 调系统
系统调数据库
执行体调任务层
而不是一个巨型 Python 文件什么都干。

### 核心点4：事件和任务要分开

这是最关键的系统设计思想之一。
Event 是“发生了什么”
例如：
illegal_parking_detected
lane_blocked_detected
slot_freed_detected

Task 是“该怎么处理”
例如：
inspect_illegal_parking
clear_blocked_lane
notify_security
recheck_slot
如果不分开，系统就会乱。
你们未来 Unified Event Engine 的第一原则，就是 事件层与任务层分离。

### 核心点5：Agent 决策不是“聪明聊天”，而是“路由”

在这版里：
if event_type == "illegal_parking_detected":
    ...
elif event_type == "lane_blocked_detected":
    ...
看起来很简单，但这正是业务系统里最重要的东西：
规则化判断 + 可审计 + 可演进
以后你可以把这一层升级成：
规则引擎
LLM + 规则混合
优先级模型
SLA 模型
多执行体调度器
但第一版必须先可控。

## 验收标准

只要下面 6 条成立，就算过关：
你能启动服务
你能创建 Event
你能查看 Slot / Task / Event
你能让 Agent 处理 illegal parking 事件
你能看到 Agent 自动创建任务
你理解 Event、Task、State、Tool 四者关系

## 应该加的 4 个升级

### 升级1：Task 状态流转

现在任务只有 created。
你可以加：
in_progress
done
failed
并新增接口：
PUT /tasks/{task_id}/start
PUT /tasks/{task_id}/done
这样就更像真实闭环。

### 升级2：事件去重

现在重复的 illegal parking 会重复生成任务。
你可以加一条规则：
同一 slot
同一 event_type
5分钟内只生成一个任务
这就开始接近“统一事件池”。

### 升级3：执行体路由

现在 assignee 只有写死逻辑。
你可以变成：

云岗亭能处理：语音提醒、远程确认
机器人能处理：复核、取证
人工能处理：清障、驱离

这就是最小调度器。

### 升级4：区域状态

现在只处理 Slot。
下一步可以加 ZoneState：
normal
congested
blocked
high_risk
这样系统就从“对象级响应”升级到“区域级理解”。

## 建议

你现在不要急着把 LLM 塞进去。
先把这版 规则型 LangGraph Agent 跑通。
因为最重要的不是“模型多聪明”，而是先把这几个认知建立起来：

事件是输入
任务是输出
状态是中间层
API 是工具层
图结构是工作流骨架

这五件事一旦通了，你再看你们自己的 Spatial OS / Operational Twin，会非常不一样。
