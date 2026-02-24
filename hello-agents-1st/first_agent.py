import os
import re
import requests
from openai import OpenAI

# ============================
# 1. 配置阿里云百炼API
# ============================
# 请在阿里云百炼控制台获取以下信息
BAILIAN_API_KEY = "sk-e7b67a626eba47dba08ebf1005cd46eb"  # 替换为你的百炼API密钥
BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"  # 百炼API地址
BAILIAN_MODEL = "qwen-max"  # 可选的模型：qwen-max, qwen-plus, qwen-turbo

# Tavily搜索API（可选，如果需要搜索功能）
TAVILY_API_KEY = "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"  # 如果需要搜索功能，替换为你的Tavily密钥

# 如果使用环境变量，取消下面行的注释
# BAILIAN_API_KEY = os.environ.get("BAILIAN_API_KEY", "your-bailian-api-key-here")
# TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "your-tavily-api-key-here")

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


# ============================
# 4. 定义阿里云百炼LLM客户端
# ============================
class BailianClient:
    """
    阿里云百炼LLM客户端，兼容OpenAI API格式。
    """

    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def generate(self, prompt: str, system_prompt: str) -> str:
        """调用百炼API生成回应。"""
        print("正在调用阿里云百炼大语言模型...")
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
                max_tokens=500
            )

            answer = response.choices[0].message.content
            print("百炼模型响应成功。")
            return answer

        except Exception as e:
            print(f"调用百炼API时发生错误：{e}")
            return f"错误：调用语言模型服务时出错 - {str(e)}"


# ============================
# 5. 主循环实现
# ============================
def main():
    # --- 1. 配置百炼客户端 ---
    API_KEY = BAILIAN_API_KEY
    BASE_URL = BAILIAN_BASE_URL
    MODEL_ID = BAILIAN_MODEL

    # 检查API密钥是否已设置
    if API_KEY == "your-bailian-api-key-here":
        print("⚠️ 警告：请先配置阿里云百炼API密钥！")
        print("步骤：")
        print("1. 访问 https://bailian.console.aliyun.com/")
        print("2. 创建应用并获取API密钥")
        print("3. 将代码中的 BAILIAN_API_KEY 替换为你的实际密钥")
        print("\n本次将使用模拟模式演示流程。")
        run_demo_mode()
        return

    llm = BailianClient(
        model=MODEL_ID,
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
    max_cycles = 5
    for i in range(max_cycles):  # 设置最大循环次数
        print(f"\n--- 循环 {i + 1}/{max_cycles} ---")

        # 3.1. 构建Prompt
        full_prompt = "\n".join(prompt_history)

        # 3.2. 调用LLM进行思考
        llm_output = llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)
        print(f"模型输出:\n{llm_output}\n")
        prompt_history.append(llm_output)

        # 3.3. 解析并执行行动
        action_match = re.search(r"Action:\s*(.*)", llm_output, re.DOTALL)
        if not action_match:
            print("解析错误: 模型输出中未找到 Action.")
            # 尝试其他可能的格式
            action_match = re.search(r"Action：\s*(.*)", llm_output, re.DOTALL)
            if not action_match:
                break

        action_str = action_match.group(1).strip()

        # 检查是否为完成指令
        if "finish" in action_str.lower():
            # 使用正则表达式提取最终答案
            finish_match = re.search(r'finish\(answer="(.*)"\)', action_str, re.DOTALL)
            if not finish_match:
                # 尝试其他格式
                finish_match = re.search(r'finish\(answer=(.*)\)', action_str, re.DOTALL)
            if finish_match:
                final_answer = finish_match.group(1).strip('"')
                print(f"✅ 任务完成！")
                print(f"最终答案: {final_answer}")
                break
            else:
                # 直接提取引号内的内容
                quote_match = re.search(r'"([^"]*)"', action_str)
                if quote_match:
                    final_answer = quote_match.group(1)
                    print(f"✅ 任务完成！")
                    print(f"最终答案: {final_answer}")
                    break
                else:
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
            print(f"🛠️ 执行工具: {tool_name}({kwargs})")
            try:
                observation = available_tools[tool_name](**kwargs)
            except Exception as e:
                observation = f"工具执行错误: {str(e)}"
        else:
            observation = f"错误: 未定义的工具 '{tool_name}'"

        # 3.4. 记录观察结果
        observation_str = f"Observation: {observation}"
        print(f"📝 {observation_str}\n" + "=" * 40)
        prompt_history.append(observation_str)

    else:
        print(f"⚠️ 已达到最大循环次数({max_cycles})，任务未完成。")

    print("\n智能体执行结束！")


# ============================
# 6. 演示模式（无API密钥时使用）
# ============================
def run_demo_mode():
    """
    演示模式，不调用真实API，展示智能体工作流程。
    """
    print("\n=== 演示模式：智能旅行助手工作流程 ===")

    user_prompt = "你好，请帮我查询一下今天北京的天气，然后根据天气推荐一个合适的旅游景点。"
    print(f"用户输入: {user_prompt}")
    print("=" * 50)

    # 模拟第一次循环
    print("\n--- 循环 1 ---")
    thought1 = "首先需要获取北京今天的天气情况，之后再根据天气情况来推荐旅游景点。"
    action1 = 'get_weather(city="北京")'
    print(f"Thought: {thought1}")
    print(f"Action: {action1}")

    # 模拟天气查询结果
    weather_result = get_weather_simulated("北京")
    print(f"Observation: {weather_result}")

    # 模拟第二次循环
    print("\n--- 循环 2 ---")
    thought2 = "现在已经知道了北京今天的天气是晴朗且温度适中，接下来可以基于这个信息来推荐一个适合的旅游景点了。"
    action2 = 'get_attraction(city="北京", weather="晴朗")'
    print(f"Thought: {thought2}")
    print(f"Action: {action2}")

    # 模拟景点推荐结果
    attraction_result = get_attraction_simulated("北京", "晴朗")
    print(f"Observation: {attraction_result}")

    # 模拟第三次循环
    print("\n--- 循环 3 ---")
    thought3 = "已经获得了适合晴天游览的景点建议，现在可以根据这些信息给用户提供满意的答复。"
    action3 = 'finish(answer="今天北京的天气是晴朗的，气温26摄氏度，非常适合外出游玩。我推荐您去颐和园欣赏美丽的湖景和古建筑，或者前往长城体验其壮观的景观和深厚的历史意义。希望您有一个愉快的旅行！")'
    print(f"Thought: {thought3}")
    print(f"Action: {action3}")

    print("\n✅ 任务完成！")
    print(
        "最终答案: 今天北京的天气是晴朗的，气温26摄氏度，非常适合外出游玩。我推荐您去颐和园欣赏美丽的湖景和古建筑，或者前往长城体验其壮观的景观和深厚的历史意义。希望您有一个愉快的旅行！")


def get_weather_simulated(city: str) -> str:
    """模拟天气查询"""
    if city == "北京":
        return "北京当前天气: 晴朗, 气温26摄氏度"
    elif city == "上海":
        return "上海当前天气: 多云, 气温22摄氏度"
    else:
        return f"{city}当前天气: 晴朗, 气温25摄氏度"


def get_attraction_simulated(city: str, weather: str) -> str:
    """模拟景点推荐"""
    if city == "北京" and "晴朗" in weather:
        return "北京在晴天最值得去的旅游景点是颐和园，因其美丽的湖景和古建筑。另一个推荐是长城，因其壮观的景观和历史意义。"
    elif city == "上海":
        return "上海在多云天气推荐游览外滩、东方明珠和豫园。"
    else:
        return f"根据{weather}天气，推荐您游览{city}的著名景点。"


# ============================
# 主程序入口
# ============================
if __name__ == "__main__":
    print("=" * 60)
    print("智能旅行助手 - 阿里云百炼Qwen3版本")
    print("=" * 60)

    # 检查API密钥配置
    if BAILIAN_API_KEY == "your-bailian-api-key-here":
        print("⚠️ 检测到未配置阿里云百炼API密钥")
        print("运行模式选择:")
        print("1. 演示模式（无API调用，展示流程）")
        print("2. 配置模式（指导如何配置API）")

        choice = input("\n请选择 (1 或 2): ").strip()

        if choice == "2":
            print("\n配置阿里云百炼API步骤:")
            print("1. 访问 https://bailian.console.aliyun.com/")
            print("2. 登录阿里云账号")
            print("3. 在控制台创建应用")
            print("4. 获取API密钥")
            print("5. 修改代码中的以下变量:")
            print("   - BAILIAN_API_KEY = '你的API密钥'")
            print("   - BAILIAN_MODEL = 'qwen-max' (或其他模型)")
            print("\n然后重新运行程序。")
        else:
            run_demo_mode()
    else:
        print("✅ 检测到已配置阿里云百炼API密钥")
        print(f"模型: {BAILIAN_MODEL}")
        print("\n开始运行智能旅行助手...")
        main()
