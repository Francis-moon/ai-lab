# Week3 - 调用大模型API（最小模板）

1，创建虚拟环境
conda create -n llm python=3.11
conda activate llm
2，安装依赖,
pip install -r requirements.txt
3，配置环境变量
cp .env.example .env
编辑 .env 填入 OPENAI_API_KEY
4，运行
python main.py

核心点1：LLM调用“四要素”
model：用哪个模型
input/messages：给什么上下文（system / user）
输出约束：强制JSON，降低跑偏
错误处理：Key缺失、网络、JSON解析失败都要处理

核心点2：为什么强制 JSON 很关键
后续第5–8周要做状态机/事件系统/对象模型，都需要结构化输入输出。
你们战略里说“对象-事件-任务-结果”的闭环数据资产，本质就是结构化数据流。

核心点3：成本与稳定性（CEO必须盯）
先用轻量模型（gpt-4o-mini）做结构化规划
计划与工具调用一旦稳定，再升级更强模型
每次输出都做 JSON 校验，失败就重试或收紧提示词。
