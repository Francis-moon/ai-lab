import re
import requests
from openai import OpenAI
from dotenv import load_dotenv
import os


# ============================
# 1. 配置大模型API
# ============================
load_dotenv()  # 从 .env 文件加载环境变量
API_KEY = os.getenv("API_KEY")  # API密钥
BASE_URL = os.getenv("BASE_URL")  # API地址
MODEL = os.getenv("MODEL")  # 模型名称

# Tavily搜索API（可选，如果需要搜索功能）
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")  # 搜索功能，Tavily密钥

# ============================
# 2. 定义系统提示词
# ============================
AGENT_SYSTEM_PROMPT = """
你是一个智能旅行助手。你的任务是分析用户的请求，并使用可用工具一步步地解决问题。

# 可用工具：
- 'get_weather(city: str)': 查询指定城市的实时天气。
- 'get_attraction(city: str, weather: str)': 根据城市和天气搜索推荐的旅游景点。

# 行动格式：
你的回答必须严格遵循以下格式。首先是你的思考过程，然后是你要执行的具体行动。
Thought: [这里是你的思考过程和下一步计划]
Action: [这里是你要调用的工具，格式为 function_name(arg_name="arg_value")]

# 任务完成：
当你收集到足够的信息，能够回答用户的最终问题时，你必须在 'Action:' 字段后使用 'finish(answer="...")' 来输出最终答案。

请开始吧！
"""


# ============================
# 3. 定义工具函数
# ============================

def get_weather(city: str) -> str:
    """
    通过调用 wttr.in API 查询真实的天气信息。
    这是一个免费的天气API，无需API密钥。
    """
    # API端点，我们请求JSON格式的数据
    url = f"https://wttr.in/{city}?format=j1"

    try:
        # 发起网络请求
        response = requests.get(url, timeout=10)
        # 检查响应状态码是否为200（成功）
        response.raise_for_status()
        # 解析返回的JSON数据
        data = response.json()

        # 提取当前天气状况
        current_condition = data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']

        # 格式化成自然语言返回
        return f"{city}当前天气: {weather_desc}, 气温{temp_c}摄氏度"

    except requests.exceptions.RequestException as e:
        # 处理网络错误
        return f"错误: 查询天气时遇到网络问题 - {e}"
    except (KeyError, IndexError) as e:
        # 处理数据解析错误
        return f"错误: 解析天气数据失败，可能是城市名称无效 - {e}"


def get_attraction_simple(city: str, weather: str) -> str:
    """
    简化版的景点推荐函数，不依赖Tavily API。
    使用内置的知识库来推荐景点。
    """
    # 基于城市和天气的简单推荐逻辑
    recommendations = {
        "北京": {
            "晴朗": "推荐游览故宫、天安门广场和颐和园。晴朗天气适合户外活动，可以欣赏到古建筑的雄伟。",
            "多云": "推荐参观国家博物馆、中国科技馆和798艺术区。多云天气适合室内游览。",
            "雨天": "推荐游览故宫博物院室内展区、国家大剧院和王府井购物中心。",
            "雪天": "推荐前往故宫赏雪景、逛南锣鼓巷体验老北京风情，或者去温暖的室内场所如国家图书馆。"
        },
        "上海": {
            "晴朗": "推荐游览外滩、东方明珠和豫园。晴朗天气适合在黄浦江边漫步。",
            "多云": "推荐参观上海博物馆、上海科技馆和新天地。",
            "雨天": "推荐游览上海自然博物馆、中华艺术宫和各大商场。",
            "雪天": "推荐前往城隍庙体验雪景、室内游览如上海海洋水族馆。"
        },
        "广州": {
            "晴朗": "推荐游览广州塔、白云山和珠江夜游。",
            "多云": "推荐参观广东省博物馆、广州动物园和沙面岛。",
            "雨天": "推荐游览广州科学中心、正佳广场和各大室内美食街。",
            "雪天": "广州很少下雪，但可以推荐室内活动如参观广州图书馆、体验广式早茶。"
        }
    }

    # 默认推荐
    default_rec = f"根据{weather}天气，推荐您游览{city}的著名景点。晴天适合户外景点，雨天适合室内博物馆和购物中心。"

    if city in recommendations:
        city_recs = recommendations[city]
        # 尝试匹配天气关键词
        for weather_key in city_recs:
            if weather_key in weather:
                return city_recs[weather_key]
        # 如果没有匹配的天气，返回第一个推荐
        return list(city_recs.values())[0]

    return default_rec


# 如果需要使用Tavily搜索（需要API密钥）
def get_attraction_with_tavily(city: str, weather: str) -> str:
    """
    使用Tavily搜索API获取景点推荐。
    需要TAVILY_API_KEY环境变量。
    """
    try:
        from tavily import TavilyClient

        # 检查API密钥
        if not TAVILY_API_KEY or TAVILY_API_KEY == "your-tavily-api-key-here":
            return "错误: 未配置Tavily API密钥，使用简化推荐模式。\n" + get_attraction_simple(city, weather)

        # 初始化Tavily客户端
        tavily = TavilyClient(api_key=TAVILY_API_KEY)

        # 构造查询
        query = f"{city} {weather} 天气 旅游景点 推荐"

        # 调用API
        response = tavily.search(query=query, search_depth="basic", include_answer=True)

        # 处理响应
        if response.get("answer"):
            return response["answer"]

        # 如果没有综合性回答，则格式化原始结果
        formatted_results = []
        for result in response.get("results", [])[:3]:
            formatted_results.append(f"- {result.get('title', '无标题')}: {result.get('content', '无内容')}")

        if not formatted_results:
            return f"未找到{city}在{weather}天气下的景点推荐。"

        return f"根据搜索，为您找到以下{city}的景点推荐:\n" + "\n".join(formatted_results)

    except ImportError:
        return "错误: 未安装tavily-python库，使用简化推荐。\n" + get_attraction_simple(city, weather)
    except Exception as e:
        return f"搜索时出错: {e}，使用简化推荐。\n" + get_attraction_simple(city, weather)


# 选择使用哪个景点推荐函数
# 如果有Tavily API密钥且已安装库，使用搜索版本；否则使用简化版本
USE_TAVILY = False  # 设置为True以使用Tavily搜索

if USE_TAVILY and TAVILY_API_KEY != "your-tavily-api-key-here":
    get_attraction = get_attraction_with_tavily
else:
    get_attraction = get_attraction_simple

# 将所有工具函数放入一个字典，方便后续调用
available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
}


def format_llm_output_for_display(llm_output: str) -> str:
    """
    仅用于终端展示：
    若包含 finish(answer="...")，将 answer 中的转义换行解码为真实换行，
    方便阅读，不影响后续解析逻辑。
    """
    match = re.search(r'finish\s*\(\s*answer\s*=\s*"(.*)"\s*\)\s*$', llm_output, re.DOTALL)
    if not match:
        return llm_output

    raw_answer = match.group(1)
    try:
        import json
        decoded_answer = json.loads(f'"{raw_answer}"')
    except Exception:
        decoded_answer = raw_answer.replace("\\\\n", "\n").replace("\\n", "\n").replace('\\"', '"')

    # 统一兜底，避免双转义场景下仍显示 \n
    decoded_answer = decoded_answer.replace("\\\\n", "\n").replace("\\n", "\n")
    pretty_finish = f'finish(answer="""\n{decoded_answer}\n""")'

    start, end = match.span()
    return llm_output[:start] + pretty_finish + llm_output[end:]


# ============================
# 4. 定义LLM客户端
# ============================
class LLMClient:
    """
    LLM客户端，兼容OpenAI API格式。
    """

    def __init__(self, model: str, api_key: str, base_url: str):
        self.client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        self.model = MODEL

    def generate(self, prompt: str, system_prompt: str) -> str:
        """调用LLM-API生成回应。"""
        print(f"正在调用{self.model}大语言模型...")
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                temperature=0.1,  # 低温度保证输出格式稳定
                max_tokens=800,
                reasoning_effort="low", 
                extra_body={"reasoning_split": True}
            )


            answer = response.choices[0].message.content
            print("LLM模型响应成功。")
            return answer

        except Exception as e:
            print(f"调用LLM API时发生错误：{e}")
            return f"错误：调用语言模型服务时出错 - {str(e)}"


# ============================
# 5. 主循环实现
# ============================
def main():
    # --- 1. 配置LLM客户端 ---
    llm = LLMClient(
        model=MODEL,
        api_key=API_KEY,
        base_url=BASE_URL
    )

    # --- 2. 初始化 ---
    city = input("请输入想查询的城市（例如：北京 / 上海 / London）：").strip()
    if not city:
        print("城市不能为空。")
        return

    user_prompt = f"你好，请帮我查询一下今天{city}的天气，然后根据天气推荐一个合适的旅游景点。"
    prompt_history = [f"用户请求: {user_prompt}"]
    print(f"用户输入: {user_prompt}\n" + "=" * 40)

    # --- 3. 运行主循环 ---
    max_cycles = 3
    for i in range(max_cycles):  # 设置最大循环次数
        print(f"\n--- 循环 {i + 1}/{max_cycles} ---")

        # 3.1. 构建Prompt
        full_prompt = "\n".join(prompt_history)

        # 3.2. 调用LLM进行思考
        llm_output = llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)
        display_output = format_llm_output_for_display(llm_output)
        print(f"模型输出:\n{display_output}\n")
        prompt_history.append(llm_output)

        # 3.3. 解析并执行行动：提取最后一个 Action，避免多 Action 时串台
        action_candidates = re.findall(
            r"Action[:：]\s*(.*?)(?=\n(?:Thought|Observation|Action)[:：]|\Z)",
            llm_output,
            re.DOTALL
        )
        if not action_candidates:
            print("解析错误: 模型输出中未找到 Action.")
            break

        action_str = action_candidates[-1].strip()

        # 检查是否为完成指令
        if "finish" in action_str.lower():
            # 使用贪婪匹配提取 answer，兼容答案中出现未转义双引号的情况
            finish_match = re.search(
                r'finish\s*\(\s*answer\s*=\s*"(.*)"\s*\)\s*$',
                action_str,
                re.DOTALL
            )
            if finish_match:
                raw_answer = finish_match.group(1)
                try:
                    import json
                    final_answer = json.loads(f'"{raw_answer}"')
                except Exception:
                    final_answer = raw_answer.replace("\\n", "\n").replace('\\"', '"')
                # 兜底处理双转义换行，确保最终输出按行展示
                final_answer = final_answer.replace("\\\\n", "\n").replace("\\n", "\n")
                print("任务完成！")
                print(f"最终答案:\n{final_answer}")
                break

            partial_match = re.search(r'finish\s*\(\s*answer\s*=\s*"(.*)$', action_str, re.DOTALL)
            if partial_match:
                raw_answer = partial_match.group(1).strip()
                final_answer = raw_answer.replace("\\\\n", "\n").replace("\\n", "\n").replace('\\"', '"')
                print("任务完成！（检测到模型输出可能被截断）")
                print(f"最终答案:\n{final_answer}")
                break

            print(f"完成指令格式无法解析: {action_str}")
            break

        # 解析工具调用
        # 匹配模式: tool_name(arg_name="arg_value")
        tool_match = re.match(r'(\w+)\((.*)\)', action_str)
        if not tool_match:
            print(f"工具调用格式错误: {action_str}")
            # 尝试其他可能的格式
            print("尝试其他格式解析...")
            continue

        tool_name = tool_match.group(1)
        args_str = tool_match.group(2)

        # 解析参数
        kwargs = {}
        try:
            # 使用正则表达式匹配 key="value" 格式
            args = re.findall(r'(\w+)\s*=\s*"([^"]*)"', args_str)
            for key, value in args:
                kwargs[key] = value
        except:
            print(f"参数解析错误: {args_str}")
            # 尝试简单分割
            if "=" in args_str:
                parts = args_str.split(",")
                for part in parts:
                    if "=" in part:
                        key_val = part.split("=")
                        if len(key_val) == 2:
                            key = key_val[0].strip()
                            val = key_val[1].strip().strip('"\'')
                            kwargs[key] = val

        # 执行工具调用
        if tool_name in available_tools:
            print(f"执行工具: {tool_name}({kwargs})")
            try:
                observation = available_tools[tool_name](**kwargs)
            except Exception as e:
                observation = f"工具执行错误: {str(e)}"
        else:
            observation = f"错误: 未定义的工具 '{tool_name}'"

        # 3.4. 记录观察结果
        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "=" * 40)
        prompt_history.append(observation_str)

    else:
        print(f"已达到最大循环次数({max_cycles})，任务未完成。")

    print("\n智能体执行结束！")


# ============================
# 主程序入口
# ============================
if __name__ == "__main__":
    print("=" * 60)
    print(f"智能旅行助手 - LLM版本")
    print("=" * 60)

    # 检查API密钥配置
    if not API_KEY or API_KEY == "your-api-key-here":
        print("检测到未配置LLM-API密钥")
        print("运行模式选择:")
        print("1. 演示模式（无API调用，展示流程）")
        print("2. 配置模式（指导如何配置API）")

        choice = input("\n请选择 (1 或 2): ").strip()

        if choice == "2":
            print("\n配置LLM-API步骤:")
            print("   .env中配置API_KEY, BASE_URL和MODEL")
            print("\n然后重新运行程序。")
        else:
            raise SystemExit("请配置API密钥后再运行程序。")
    else:
        print("检测到已LLM-API密钥")
        load_dotenv
        model = os.getenv("MODEL")
        print(f"模型: {model}")
        print("\n开始运行智能旅行助手...")
        main()

