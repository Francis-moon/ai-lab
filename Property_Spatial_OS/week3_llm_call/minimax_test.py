import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")  # 从环境变量中获取API密钥
base_url = os.getenv("MODEL_URL")  # 从环境变量中获取模型URL
model = os.getenv("MODEL")  # 从环境变量中获取模型名称

# 初始化客户端
client = OpenAI(
    api_key=api_key,  # 使用从环境变量中获取的API密钥
    base_url=base_url  # 使用从环境变量中获取的模型URL
)

# 调用模型（与OpenAI使用方式完全相同）
response = client.chat.completions.create(
    model=model,    # 使用从环境变量中获取的模型名称
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hi, how are you?"},
    ],
    # 设置 reasoning_split=True 将思考内容分离到 reasoning_details 字段
    extra_body={"reasoning_split": True},
)

print(f"Thinking:\n{response.choices[0].message.reasoning_details[0]['text']}\n")
print(f"Text:\n{response.choices[0].message.content}\n")