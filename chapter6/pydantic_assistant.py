"""
智能搜索助手 - 基于 Pydantic AI 的真实搜索系统

突出 Pydantic AI 的核心特点：
1. deps_type：把 Tavily client 等外部依赖，通过 RunContext 注入，而不是用全局变量
2. output_type：用 Pydantic BaseModel 定义结构化输出，模型必须按 schema 返回，天然可验证
3. @agent.tool：用普通函数 + docstring 注册工具，Pydantic AI 自动生成 tool schema
4. message_history：多轮对话直接传历史消息列表，不需要像 LangGraph 那样手动搭建 StateGraph
"""

import asyncio
import os
from dataclasses import dataclass
from typing import Literal

import logfire
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits
from tavily import TavilyClient

load_dotenv()

logfire.configure()
logfire.instrument_pydantic_ai()


# 依赖注入：把外部客户端包装成 dataclass，通过 deps 传给 Agent
@dataclass
class SearchDeps:
    tavily_client: TavilyClient


# 基于搜索结果整理出的最终回答
class SearchAnswer(BaseModel):
    summary: str = Field(description="对用户问题的简洁回答，1-3句话")
    key_points: list[str] = Field(description="支撑回答的关键信息点，条目式列出")
    sources: list[str] = Field(default_factory=list, description="应用到的信息来源 URL")
    confidence: Literal["high", "medium", "low"] = Field(
        description="回答的置信度：high=有明确搜索结果支撑，medium=部分信息缺失，low=主要靠模型自身知识"
    )


model = OpenAIChatModel(
    os.getenv("MODEL_ID"),
    provider=OpenAIProvider(
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("BASE_URL"),
    ),
)

search_agent = Agent(
    model=model,
    deps_type=SearchDeps,
    output_type=SearchAnswer,
    instructions=(
        "你是一个搜索助手。当用户的问题涉及时效性信息、具体事实、"
        "或者你不确定答案时，必须调用 web_search 工具查证，"
        "不要凭空编造。可以多次调用工具来补充信息。"
        "最终答案要基于搜索结果，并在 sources 中列出引用的 URL。"
        "如果搜索失败或没有结果，可以基于自身知识回答，但要把 confidence 设为 low。"
        "如果连续两次搜索结果高度相似，说明已经拿到足够信息，直接基于现有结果给出答案，不要重复搜索相同或相近的关键词。"
    ),
)


# 注册工具：普通函数 + docstring，Pydantic AI 自动生成 tool schema 给模型用
@search_agent.tool
async def web_search(ctx: RunContext[SearchDeps], query: str) -> str:
    """使用 Tavily 搜索引擎查询实时信息。

    Args:
        query: 搜索关键词，尽量精准、简洁
    """

    # 简单去重：记录本次 run 里已经搜过的 query
    seen = getattr(ctx.deps, "_seen_queries", None)
    if seen is None:
        seen = ctx.deps._seen_queries = set()

    normalized = query.replace(" ", "")
    if any(normalized in s or s in normalized for s in seen):
        return "你已经用非常相似的关键词搜索过了，结果不会有实质变化。请直接基于已获得的信息给出最终答案，不要再次调用 web_search。"

    try:
        print(f"🔍 正在搜索: {query}")
        response = ctx.deps.tavily_client.search(
            query=query,
            search_depth="basic",
            include_answer=True,
            include_raw_content=False,
            max_results=5,
        )
    except Exception as e:
        # 用 ModelRetry 告知模型这次工具调用失败，模型可以换个关键词重试，
        # 而不是直接把异常抛给整个程序
        raise ModelRetry(f"搜索失败：{e!s}，请尝试更换搜索关键词。") from e

    parts = []
    if response.get("answer"):
        parts.append(f"综合答案：\n{response['answer']}")

    if response.get("results"):
        for i, result in enumerate(response["results"][:3], 1):
            title = result.get("title", "")
            content = result.get("content", "")
            url = result.get("url", "")
            parts.append(f"{i}. {title}\n{content}\n来源：{url}")

    if not parts:
        return "没有找到相关信息，可以尝试换一个更具体或更宽泛的关键词。"

    return "\n\n".join(parts)


# 主循环：多轮对话通过 message_history 维护上下文
async def main():
    if not os.getenv("TAVILY_API_KEY"):
        print("❌ 错误：请在 .env 文件中配置 TAVILY_API_KEY")
        return

    deps = SearchDeps(tavily_client=TavilyClient(api_key=os.getenv("TAVILY_API_KEY")))

    print("🔍 智能搜索助手启动！（Pydantic AI 版）")
    print("我会按需调用 Tavily 搜索工具，为您整理结构化的答案")
    print("(输入 'quit' 退出)\n")

    # 用一个列表保存历史消息，实现多轮对话记忆
    message_history: list[ModelMessage] = []
    session = PromptSession(history=InMemoryHistory())

    while True:
        try:
            user_input = (await session.prompt_async("🤔 您想了解什么: ")).strip()
        except (KeyboardInterrupt, EOFError):
            print("感谢使用！再见！👋")
            break

        if user_input.lower() in ["quit", "q", "exit", "退出"]:
            print("感谢使用！再见！👋")
            break

        if not user_input:
            continue

        try:
            print("\n" + "=" * 60)
            result = await search_agent.run(
                user_input,
                deps=deps,
                message_history=message_history,
                usage_limits=UsageLimits(request_limit=5),
            )

            answer = result.output
            print(f"\n💡 回答: {answer.summary}\n")
            if answer.key_points:
                print("关键信息：")
                for point in answer.key_points:
                    print(f"  • {point}")
            if answer.sources:
                print("\n来源：")
                for src in answer.sources:
                    print(f"  - {src}")
            print(f"\n置信度: {answer.confidence}")
            print("=" * 60 + "\n")

            # 把这一轮的消息追加进历史，供下一轮对话使用
            message_history = result.all_messages()

        except Exception as e:
            print(f"❌ 发生错误: {e}")
            print("请重新输入您的问题。\n")


if __name__ == "__main__":
    asyncio.run(main())
