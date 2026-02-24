import json
import os
from typing import Any, Dict
from dotenv import load_dotenv
from OpenAICompatibleClient import OpenAICompatibleClient


def call_llm_make_plan(client: OpenAICompatibleClient, user_task: str) -> Dict[str, Any]:
    """
    输入一个任务描述，输出结构化巡检计划（JSON）。
    这是第3周的目标：稳定把 LLM 当作“可调用组件”。
    """
    system_prompt = (
        "你是停车场运营的任务规划助手。"
        "请把用户输入的任务，转成可执行的巡检计划。"
        "必须返回严格JSON，不要包含多余文字。"
    )

    user_prompt = (
        f"任务：{user_task}\n"
        "请输出JSON，字段固定如下：\n"
        "{\n"
        '  "goal": string,\n'
        '  "steps": [ { "id": number, "action": string, "target": string, "expected_output": string } ],\n'
        '  "risks": [string],\n'
        '  "success_criteria": [string]\n'
        "}\n"
        "注意：只返回JSON对象本身，不要使用Markdown代码块。"
    )

    text = client.generate(prompt=user_prompt, system_prompt=system_prompt)
    return json.loads(text)


def main():
    load_dotenv()

    print("=== 第3周：LLM调用练习（OpenAICompatibleClient版）===")
    user_task = input("请输入任务（例如：巡检A区 / 复核12车位 / 取证乱停车辆）：").strip()
    if not user_task:
        print("任务不能为空。")
        return

    try:
        # 优先兼容当前项目命名；也允许从 OPENAI_MODEL 透传
        model = os.getenv("MODEL") or os.getenv("OPENAI_MODEL")
        client = OpenAICompatibleClient(model=model)

        plan = call_llm_make_plan(client, user_task)
        print("\n--- 结构化计划(JSON) ---")
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print("模型返回不是有效JSON。你可以：1) 重试 2) 更严格约束提示词。")
    except Exception as e:
        print(f"调用失败：{e}")


if __name__ == "__main__":
    main()
