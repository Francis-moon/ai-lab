import os

from dotenv import load_dotenv
from openai import OpenAI


class OpenAICompatibleClient:
    """调用兼容 OpenAI 接口的 LLM 客户端封装。"""
    def __init__(self, model: str = None, api_key: str = None, model_url: str = None):
        load_dotenv()
        self.model = model or os.getenv("MODEL")
        self.model_url = model_url or os.getenv("MODEL_URL")
        self.api_key = (
            api_key
            or os.getenv("API_KEY")
        )
        if not self.api_key:
            raise ValueError("未找到 API Key，请在 .env 中配置 API_KEY")

        self.client = OpenAI(api_key=self.api_key, base_url=self.model_url)

    def generate(self, prompt: str, system_prompt: str) -> str:
        """调用 LLM，返回文本内容。"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            stream=False,
        )
        return (response.choices[0].message.content or "").strip()


if __name__ == "__main__":
    client = OpenAICompatibleClient()
    system_prompt = "你是一个严谨专业的AI助手。"
    user_prompt = "你好，请介绍一下你自己，包括你的型号。"
    answer = client.generate(user_prompt, system_prompt)
    print("模型返回：", answer)
