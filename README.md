一个 12周（3个月）实操型学习路线。
目标非常明确：
3个月后，你可以独立搭建一个“类 Parking Spatial OS 的简化版 Agent 系统原型”。

每周都包含：
🎯 本周目标
📚 学习资料（具体网址）
🛠 实操步骤（可直接照做）
🧪 练习任务（必须完成）

技术栈统一：
Python + FastAPI + OpenAI API + LangGraph + SQLite
避免过度复杂。

总体结构:
阶段一（1–4周）：恢复工程能力 + 单Agent
阶段二（5–8周）：状态机 + 事件系统 + 语义对象
阶段三（9–12周）：多Agent调度 + 闭环系统

第1周：恢复Python能力
🎯 目标
掌握Python基础语法，能写函数、类、简单逻辑。

📚 学习资料
1️⃣ Python官方教程（前4章）
https://docs.python.org/3/tutorial/

2️⃣ 廖雪峰Python教程（第1–6节）
https://www.liaoxuefeng.com/wiki/1016959663602400

🛠 实操步骤
创建项目目录：
mkdir ai_lab
cd ai_lab
python3 -m venv venv
source venv/bin/activate

创建文件：
touch main.py
🧪 练习任务
写一个函数：
def inspect_slot(slot_id):
    print(f"{slot_id} inspected")
定义类：
class Slot:
    def __init__(self, slot_id, state):
        self.slot_id = slot_id
        self.state = state
创建10个Slot对象并打印状态。

完成标准：
能运行python main.py
无报错
能理解类与函数区别

第2周：API与JSON
🎯 目标
理解API调用与JSON数据结构。
📚 学习资料
1️⃣ JSON基础
https://www.w3schools.com/js/js_json_intro.asp

2️⃣ Python requests库
https://requests.readthedocs.io/en/latest/

🛠 实操
安装requests：
pip install requests

写代码调用公开API：
import requests
response = requests.get("https://api.github.com")
print(response.json())

🧪 练习
调用一个天气API（任选）
解析返回JSON
提取其中一个字段

完成标准：
能理解JSON字典结构
能用response.json()["key"]

第3周：调用大模型API
🎯 目标
能调用OpenAI API并得到回复。

📚 学习资料
OpenAI API文档：
https://platform.openai.com/docs

Python示例：
https://platform.openai.com/docs/guides/text-generation

🛠 实操
pip install openai
示例代码：
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "设计一个巡检计划"}
    ]
)

print(response.choices[0].message.content)

🧪 练习
输入“巡检A区”
输出3步执行计划

完成标准：
能稳定调用API
能打印模型回复

第4周：Tool Calling（Agent雏形）
🎯 目标
理解LLM调用工具。

📚 学习资料
Function Calling文档：
https://platform.openai.com/docs/guides/function-calling

🛠 实操
定义工具：
tools = [
    {
        "type": "function",
        "function": {
            "name": "inspect_slot",
            "parameters": {
                "type": "object",
                "properties": {
                    "slot_id": {"type": "string"}
                }
            }
        }
    }
]

让模型调用函数。

🧪 练习
构建流程：
用户输入 → 模型判断 → 调用函数 → 输出结果
完成标准：
模型能自动选择工具
理解Tool Use机制

第5周：状态机
🎯 目标
构建Slot状态系统。

📚 学习资料
Python状态机库：
https://github.com/pytransitions/transitions

🛠 实操
pip install transitions

定义状态：
Free → Occupied → Illegal → Cleared

🧪 练习
定义状态转移规则
触发事件改变状态
打印状态变化日志

完成标准：
状态不可非法跳转
理解事件驱动

第6周：事件驱动系统
🎯 目标
实现：
event → 状态更新 → 生成任务

🛠 实操
定义：
class Event:
    def __init__(self, type, target):
        self.type = type
        self.target = target
写事件循环：
while events:
    handle_event(event)

🧪 练习
模拟IllegalParking事件
自动生成Inspect任务

完成标准：
事件能驱动业务流程

第7周：语义对象模型
🎯 目标
实现简化版 Parking Semantic Map。

🛠 实操
定义：
class Lane
class Zone
class Slot

维护关系：
slot.zone = zoneA

🧪 练习
构建3个Zone
每个Zone 5个Slot
查询某Zone空闲车位

完成标准：
能进行对象级查询

第8周：数据库存储
🎯 目标
把对象和状态存入数据库。

📚 学习资料

SQLite + SQLAlchemy
https://docs.sqlalchemy.org/

🛠 实操
pip install sqlalchemy
定义Slot表并存储状态。

🧪 练习

插入100个Slot

更新状态

查询历史记录

完成标准：

数据持久化成功

第9周：FastAPI接口层

🎯 目标
构建简单API服务。

📚 学习资料

https://fastapi.tiangolo.com/

🛠 实操

pip install fastapi uvicorn

创建接口：

@app.get("/slots")

🧪 练习

查询所有Slot

修改Slot状态

完成标准：

浏览器能访问API

第10周：LangGraph（真正Agent系统）

🎯 目标
构建有状态Agent流程。

📚 学习资料

LangGraph：

https://langchain-ai.github.io/langgraph/

🛠 实操

构建Graph：

Planner → Tool → UpdateState → End

🧪 练习

实现完整流程：

输入巡检 → 生成任务 → 更新状态

完成标准：

形成闭环

第11周：多Agent模拟

🎯 目标
模拟3个机器人调度。

🛠 实操

定义：

class Robot:
    battery
    current_task

写调度函数：

优先级排序

电量判断

🧪 练习

模拟：

10任务
3机器人

输出调度日志。

完成标准：

无冲突执行

第12周：整合成简化Spatial OS

🎯 目标
整合：
语义对象
状态机
事件系统
Agent
调度器
API接口
形成一个可运行系统。

最终成果：
你将拥有一个：
可输入事件
自动生成任务
多机器人分配
状态实时更新
可查询数据库
可API调用
的完整小系统。

每周学习时间
建议：
周六 3小时
周日 3小时
不需要更多。