import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

import tools as local_tools


def must_get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"缺少环境变量 {name}。请检查 .env 是否配置。")
    return v


def build_tools_spec() -> List[Dict[str, Any]]:
    """定义可被模型调用的工具“规格”（JSON Schema）。
    这里我们将本地定义的工具转换为模型可理解的规格。
    注意：name必须和tools.py中定义的工具函数名一致。
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_slot_state",
                "description": "查询车位状态（Free, Occupied, Illegal等）与归属区域",
                "parameters": {
                    "type": "object",
                    "properties": {"slot_id": {"type": "int"}},
                    "required": ["slot_id"]
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "inspect_slot",
                "description": "对指定车位执行巡检并返回巡检记录/证据ID",
                "parameters": {
                    "type": "object",
                    "properties": {"slot_id": {"type": "int"}},
                    "required": ["slot_id", "reason"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "capture_evidence",
                "description": "对指定车位进行取证（例如乱停、堵塞等），返回照片/证据ID",
                "parameters": {
                    "type": "object",
                    "properties": {"slot_id": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["slot_id", "reason"],
                },
            },
        },
    ],

        