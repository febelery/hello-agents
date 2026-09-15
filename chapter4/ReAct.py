import re
from datetime import datetime

from llm_client import LLMClient
from tools import ToolExecutor, search

"""
ReAct (Reasoning and Acting)： 一种将“思考”和“行动”紧密结合的范式，让智能体边想边做，动态调整。

适用于以下场景：
- 需要外部知识的任务：如查询实时信息（天气、新闻、股价）、搜索专业领域的知识等。
- 需要精确计算的任务：将数学问题交给计算器工具，避免LLM的计算错误。
- 需要与API交互的任务：如操作数据库、调用某个服务的API来完成特定功能。
"""

REACT_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。
当前现实时间是：{current_date}。在涉及“最新”、“今年”等时间敏感问题时，请以此时间为基准进行推断与检索，切勿默认局限于你过往的预训练年份。

可用工具如下：
{tools}

请严格按照以下格式进行回应。每轮交互仅输出一次 Thought 和一次 Action，绝对不要自行编造 Observation：

Thought: 你的思考过程，用于分析问题、拆解任务和规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一：
- `{{tool_name}}[{{tool_input}}]`: 调用一个可用工具。
- `Finish[{{final_answer}}]`: 当你收集到足够的信息，能够回答用户的最终问题时，在方括号内填入完整的最终答案。

现在，请开始解决以下问题：
Question: {question}
History: {history}
"""


class ReActAgent:
    def __init__(
        self, llm_client: LLMClient, tool_executor: ToolExecutor, max_steps: int = 5
    ):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []

    def run(self, question: str):
        self.history = []
        current_step = 0
        current_date = datetime.now().astimezone().strftime("%Y年%m月%d日")

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")

            tool_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            prompt = REACT_PROMPT_TEMPLATE.format(
                current_date=current_date,
                tools=tool_desc,
                question=question,
                history=history_str,
            )

            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)
            if not response_text:
                print("错误：LLM未能返回有效响应。")
                break

            thought, action = self._parse_output(response_text)
            if thought:
                print(f"🤔 思考: {thought}")
            if not action:
                print("警告：未能解析出有效的Action，流程终止。")
                break

            if action.startswith("Finish"):
                # 如果是Finish指令，提取最终答案并结束
                final_answer = self._parse_action_input(action)
                print(f"🎉 最终答案: {final_answer}")
                return final_answer

            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                self.history.append("Observation: 无效的Action格式，请检查。")
                continue

            print(f"🎬 行动: {tool_name}[{tool_input}]")
            tool_function = self.tool_executor.getTool(tool_name)
            observation = (
                tool_function(tool_input)
                if tool_function
                else f"错误：未找到名为 '{tool_name}' 的工具。"
            )

            print(f"👀 观察: {observation}")
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

        print("已达到最大步数，流程终止。")
        return None

    def _parse_output(self, text: str):
        # Thought: 匹配到 Action: 或文本末尾
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        # Action: 遇到换行后的 Observation:、Thought: 或文本末尾即停止，防止吞入模型自编的多步内容
        action_match = re.search(
            r"Action:\s*(.*?)(?=\nObservation:|\nThought:|$)", text, re.DOTALL
        )
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def _parse_action(self, action_text: str):
        # 使用非贪婪匹配，避免捕获多余括号或后续文本
        match = re.match(r"(\w+)\[(.*?)\]", action_text, re.DOTALL)
        return (match.group(1), match.group(2)) if match else (None, None)

    def _parse_action_input(self, action_text: str):
        match = re.search(r"Finish\[(.*?)\]", action_text, re.DOTALL)
        content = match.group(1).strip() if match else ""
        # 若模型将“最终答案”字面量填入括号，而把真实答案写在后面，则做兼容提取
        if content == "最终答案" or not content:
            after = re.sub(
                r"^Finish(\[.*?\])?\s*:?", "", action_text, flags=re.DOTALL
            ).strip()
            if after:
                return after
        return content


if __name__ == "__main__":
    llm = LLMClient()
    tool_executor = ToolExecutor()

    search_desc = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    tool_executor.registerTool("Search", search_desc, search)
    agent = ReActAgent(llm_client=llm, tool_executor=tool_executor)
    question = "Apple最新的手机是哪一款？它的主要卖点是什么？"
    agent.run(question)
