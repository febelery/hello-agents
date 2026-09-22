"""语义路由器（Semantic Router）

遵循设计模式原则：
- 单一职责（SRP）：仅负责根据用户输入进行语义理解并路由到合适的目标处理器。
- 依赖注入（DI）：通过构造函数注入 TypeSafeClient，便于单元测试与 Mock。
- KISS：采用简单的字典分发表，不搞过度设计的动态反射机制。
"""

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from typesafe_sdk import Choice, TypeSafeClient

from chapter5.client import get_typesafe_client

console = Console()


@dataclass
class RouteDecision:
    """路由决策结果"""

    route_name: str
    confidence: float
    reason: str


class SemanticRouter:
    """基于 Jev 的极速语义路由器"""

    def __init__(self, client: TypeSafeClient | None = None):
        # 依赖注入：如果不传入则使用默认配置
        self.client = client or get_typesafe_client()
        self._handlers: dict[str, Callable[[str], str]] = {}

    def register(self, route_name: str, handler: Callable[[str], str]) -> None:
        """注册分支对应的处理函数"""
        self._handlers[route_name] = handler

    def decide(self, text: str) -> RouteDecision:
        """分析文本语义，返回最适合的路由分支"""
        response = self.client.system_one(
            state=text,
            questions={
                "target_route": Choice(
                    instructions="判定用户输入应当分发给哪类业务专家处理",
                    criteria={
                        "code_assistant": "编写、重构代码，技术实现细节，算法或代码 Debug",
                        "product_support": "产品功能咨询、价格政策、账号问题、使用指南",
                        "chitchat": "纯粹日常打招呼、闲聊、情感交流或无关内容",
                    },
                )
            },
        )
        answer = response.answers["target_route"]
        return RouteDecision(
            route_name=answer.choice,
            confidence=answer.confidence,
            reason=f"命中 {answer.choice} 分支，置信度 {answer.confidence:.2f}",
        )

    def route(self, text: str) -> str:
        """执行路由决策并调用对应的 Handler"""
        decision = self.decide(text)
        console.print(
            f"[bold cyan]🔍 路由决策:[/bold cyan] {decision.route_name} (置信度: {decision.confidence:.2f})"
        )

        handler = self._handlers.get(decision.route_name)
        if not handler:
            return f"[Default Fallback] 未找到针对 {decision.route_name} 的处理器。"
        return handler(text)


# --- 运行验证 ---
if __name__ == "__main__":
    print()
    console.rule("[bold cyan]Jev 语义路由器（Semantic Router）实战演示[/bold cyan]")
    print()

    router = SemanticRouter()

    # 注册处理函数
    router.register(
        "code_assistant", lambda q: f"🛠️ [代码工作台] 正在调用代码环境分析: '{q}'"
    )
    router.register(
        "product_support", lambda q: f"💼 [产品支持组] 正在检索 SaaS 商业知识库: '{q}'"
    )
    router.register("chitchat", lambda q: "💬 [闲聊助手] 你好呀，今天有什么想聊的？")

    test_queries = [
        "你能帮我用 Python 实现一个快速排序算法吗？",
        "你们的专业版套餐支持按月订阅吗？多少钱？",
        "今天天气真不错，你平时喜欢听什么音乐呀？",
    ]

    for idx, query in enumerate(test_queries, 1):
        print()
        console.print(f"[bold cyan]测试用例 #{idx}[/bold cyan]")
        console.print(f"  📥 [bold white]用户输入:[/bold white] {query}")
        result = router.route(query)
        console.print(f"  📤 [bold green]分发执行:[/bold green] {result}")

    print()
    console.rule("[dim]演示完毕[/dim]")
    print()
