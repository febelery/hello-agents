import os
import re

from dotenv import load_dotenv

from chapter1.llm import OpenAICompatibleClient
from chapter1.tools import *

load_dotenv()


llm = OpenAICompatibleClient(
    model=os.environ["MODEL_ID"],
    api_key=os.environ["API_KEY"],
    base_url=os.environ["BASE_URL"],
)

# 初始化
user_prompt = "你好，请帮我查询一下今天成都的天气，然后根据天气推荐一个合适的旅游景点。"
prompt_history = [f"用户请求: {user_prompt}"]
agent_system_prompt = """
你是一个智能旅行助手，你的任务是分析用户的请求，并使用可用工具一步步的解决问题。

# 可用工具
- `get_weather(city: str)`: 查询指定城市的实时天气。
- `get_attraction(city: str, weather: str)`: 根据城市和天气搜索推荐的旅游景点。

# 输出格式要求：
你的每次回复必须严格遵循一下格式, 包含一堆Thought和Action:

Thought: [你的思考过程和下一步计划]
Action: [你要执行的具体行动]

Action的格式必须是以下之一:
1. 调用工具: function_name(arg_name="arg_value")
2. 结束任务： Finish[最终答案]

# 决策规则
每一轮都检查当前已有的信息是否足够回答用户问题。
如果信息不足：调用合适的工具。
如果信息已经足够：不要再调用工具，直接使用 Finish 返回最终答案。

# 重要提示：
- 每次只输出一堆Thought-Action
- Action必须在同一行, 不要换行
- 当收集到足够信息可用回答用户问题时，必须使用 Action: Finish[最终答案] 格式结束


"""
available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
}


print(f"用户输入: {user_prompt}\n" + "=" * 40)


# 运行主循环
for i in range(5):  # 设置最大循环次数
    print(f"--- 循环 {i + 1} ---\n")

    full_prompt = "\n".join(prompt_history)

    # 调用LLM进行思考
    llm_output = llm.generate(full_prompt, system_prompt=agent_system_prompt)

    # 模型可能会输出多余的Thought-Action，需要截断
    match = re.search(
        r"(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)",
        llm_output,
        re.DOTALL,
    )
    if match:
        truncated = match.group(1).strip()
        if truncated != llm_output.strip():
            llm_output = truncated
            print("已截断多余的 Thought-Action 对")

    print(f"模型输出:\n{llm_output}\n")
    prompt_history.append(llm_output)

    # 解析并执行行动
    action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
    if not action_match:
        observation = "错误： 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。"
        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "=" * 40)
        prompt_history.append(observation_str)
        continue
    action_str = action_match.group(1).strip()

    if action_str.startswith("Finish"):
        final_answer = re.match(r"Finish\[(.*)\]", action_str).group(1)
        print(f"任务完成，最终答案: {final_answer}")
        break

    tool_name = re.search(r"(\w+)\(", action_str).group(1)
    args_str = re.search(r"\((.*)\)", action_str).group(1)
    kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

    if tool_name in available_tools:
        observation = available_tools[tool_name](**kwargs)
    else:
        observation = f"错误：未定义的工具 '{tool_name}'"

    # 记录观察结果
    observation_str = f"Observation: {observation}"
    print(f"{observation_str}\n" + "=" * 40)
    prompt_history.append(observation_str)
