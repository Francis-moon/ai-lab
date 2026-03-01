import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

import tools as local_tools


# ============================
# 1. 环境变量读取
# ============================
def must_get_env(name: str) -> str:
    """
    读取必填环境变量，不存在就直接报错，避免后续请求时才失败。
    """
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"缺少环境变量 {name}。请检查 week4_tool_calling/.env 配置。")
    return value


# ============================
# 2. 工具规格（给模型看的“说明书”）
# ============================
def build_tools_spec() -> List[Dict[str, Any]]:
    """
    定义可被模型调用的本地工具规格（JSON Schema）。
    告诉模型有哪些工具可用，每个工具的功能是什么，需要什么参数。
    注意：name 必须和 tools.py 中函数名一致。
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_slot_state",
                "description": "查询车位状态（Free/Occupied/Illegal）与所属区域",
                "parameters": {
                    "type": "object",
                    "properties": {"slot_id": {"type": "integer"}},
                    "required": ["slot_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "inspect_slot",
                "description": "巡检指定车位并返回巡检记录/证据ID",
                "parameters": {
                    "type": "object",
                    "properties": {"slot_id": {"type": "integer"}},
                    "required": ["slot_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "capture_evidence",
                "description": "对指定车位取证（如乱停、堵塞等），返回证据ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "slot_id": {"type": "integer"},
                        "reason": {"type": "string"},
                    },
                    "required": ["slot_id", "reason"],
                },
            },
        },
    ]


# ============================
# 3. 工具执行与参数处理
# ============================
def _coerce_slot_id(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    兼容模型把 slot_id 传成字符串的情况，统一转成 int。
    """
    if "slot_id" in arguments and isinstance(arguments["slot_id"], str):
        raw = arguments["slot_id"].strip()
        if raw.isdigit():
            arguments["slot_id"] = int(raw)
    return arguments


def execute_local_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    按名称执行 tools.py 里的本地函数，并将结果包装为结构化返回给模型。
    """
    fn = getattr(local_tools, name, None)    #根据名字找到tools.py中对应的函数
    if fn is None:
        return {"error": f"Unknown tool: {name}"}

    try:
        safe_args = _coerce_slot_id(arguments or {})
        return fn(**safe_args)   #把模型传来的参数解包成函数参数来调用
    except TypeError as e:
        return {"error": f"Bad arguments for {name}: {e}"}
    except Exception as e:
        return {"error": f"Tool {name} failed: {e}"}


# ============================
# 4. 输出解析
# ============================
def _parse_json_text(text: str) -> Optional[Dict[str, Any]]:
    """
    优先按纯 JSON 解析；若模型前后夹带文字，尝试提取第一个对象。
    """
    text = (text or "").strip()
    if not text:
        return None

    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


# ============================
# 5. Agent 主流程（Chat Completions Tool Calling）
# ============================
def run_agent_with_tools(client: OpenAI, model: str, user_task: str) -> Dict[str, Any]:
    """
    为什么用 chat.completions：
    - 你当前网关是 OpenAI 兼容接口（如 MiniMax），常见不支持 responses API。
    - chat.completions + tools 兼容性更高，可避免 404 page not found。
    """
    tools_spec = build_tools_spec()
    system_prompt = (
        "你是停车场运营任务代理Agent。你可以调用工具完成巡检与取证。"
        "1)请先判断是否需要调用工具（查询状态/巡检/取证）。"
        "2)如需要，必须调用，拿到结果后继续推理。"
        "3)最终只输出 JSON 对象（不要夹带多余文字），格式为："
        "最终JSON格式：\n"
        "{\n"
        '  "goal": string,\n'
        '  "tool_calls": [ { "name": string, "arguments": object, "tool_result": object } ],\n'
        '  "final_steps": [ { "id": number, "action": string, "target": string, "expected_output": string } ],\n'
        '  "success_criteria": [string]\n'
        "}\n"
    )

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"任务：{user_task}"},
    ]
    tool_calls_log: List[Dict[str, Any]] = []
    final_text = ""

    # 最多循环 8 轮，防止异常情况下无限调用工具
    for _ in range(8):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools_spec,
            tool_choice="auto",
            temperature=0,
        )
        msg = resp.choices[0].message
        tool_calls = msg.tool_calls or []

        # 模型提出工具调用：执行工具 -> 把结果作为 tool 消息回传给模型
        if tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in tool_calls
                    ],
                }
            )

            for tc in tool_calls:
                name = tc.function.name
                raw_args = tc.function.arguments or "{}"
                try:
                    arguments = json.loads(raw_args)
                    if not isinstance(arguments, dict):
                        arguments = {"_raw": raw_args}
                except json.JSONDecodeError:
                    arguments = {"_raw": raw_args}

                result = execute_local_tool(name, arguments)
                # 把调用过程写入 tool_calls_log（便于审计/回放，“证据链”）
                tool_calls_log.append(
                    {"name": name, "arguments": arguments, "tool_result": result}
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
            continue

        # 没有工具调用，说明模型给了最终文本
        final_text = msg.content or ""
        break

    final_obj = _parse_json_text(final_text)
    if final_obj is None:
        # 若模型没按 JSON 输出，保底返回结构化结果，便于排查
        final_obj = {
            "goal": user_task,
            "tool_calls": tool_calls_log,
            "final_steps": [],
            "success_criteria": [],
            "raw_output": final_text,
        }
    elif "tool_calls" not in final_obj:
        # 模型漏写 tool_calls 时，用我们本地日志补齐
        final_obj["tool_calls"] = tool_calls_log

    return final_obj


# ============================
# 6. 入口
# ============================
def main() -> None:
    load_dotenv()
    api_key = must_get_env("API_KEY")
    model = must_get_env("MODEL")
    base_url = must_get_env("BASE_URL")

    client = OpenAI(api_key=api_key, base_url=base_url)

    print("=== 第4周：Tool Calling（本地工具调用）===")
    user_task = input("请输入任务（例：复核12车位并取证 / 巡检A区12车位）：").strip()
    if not user_task:
        print("任务不能为空。")
        return

    try:
        result = run_agent_with_tools(client, model, user_task)
        print("\n--- 最终输出(JSON) ---")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"运行失败：{e}")


if __name__ == "__main__":
    main()
