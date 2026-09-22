"""TypeSafe Jev 核心架构模式（Design Patterns）

在工程落地中，Jev 作为 System One 模型，具备“无状态、高并发、确定性类型、输出校准概率”的特点。
本模块演示三种最常见的核心架构模式：
1. 并发展开 (Speculative Fan-out)：一次调用挂载多维度假设，由业务代码选择消费分支。
2. 复合评分 (Composite Scoring)：将多个原语的判断与概率转化为加权业务分值，支持代码动态调权。
3. 置信度降级 (Confidence Escalation)：依据分布集中度与阈值自动触发回退或人工介入。
"""

from client import get_typesafe_client
from rich.console import Console
from rich.panel import Panel
from typesafe_sdk import Choice, Noul, Score

console = Console()


def pattern_fan_out():
    """模式一：并发展开与推测式问询 (Speculative Fan-out)"""
    print()
    console.rule(
        "[bold green]模式一：并发展开与推测式问询 (Speculative Fan-out)[/bold green]"
    )
    print()

    client = get_typesafe_client()
    message = "我上周订购的机械键盘今天收到时外包装已经破损，轴体按压卡顿，我需要换货或者退款！"

    console.print(Panel(message, title="[green]客户消息[/green]", border_style="green"))
    print(
        "⏳ 并发评估 [意图识别] + [推测分支A: 商品物理损坏] + [推测分支B: 客户情绪不满]..."
    )

    response = client.system_one(
        state=message,
        questions={
            "intent": Choice(
                instructions="用户的主要诉求是什么？",
                criteria={
                    "after_sales": "售后换货或退货申请",
                    "logistics": "纯物流跟踪或催件",
                    "consultation": "售前咨询与使用答疑",
                },
            ),
            "is_product_damaged": Noul(
                instructions="用户是否反馈了商品自身存在物理损坏或质量缺陷？",
            ),
            "has_dissatisfaction": Noul(
                instructions="用户是否对本次购物体验表达了反感或强烈不满？",
            ),
        },
    )

    intent = response.answers["intent"].choice
    print()
    console.print(
        f"  • 主意图判定: [bold yellow]{intent}[/bold yellow] (置信度: {response.answers['intent'].confidence:.2f})"
    )

    if intent == "after_sales":
        damaged_prob = response.answers["is_product_damaged"].noul
        dissatisfied_prob = response.answers["has_dissatisfaction"].noul
        is_damaged = damaged_prob > 0.6

        console.print(
            f"  • [cyan]售后推测分支激活[/cyan] -> 检测到物理损坏: [bold red]{is_damaged}[/bold red] (概率: {damaged_prob:.2f})"
        )
        console.print(
            f"  • [cyan]售后推测分支激活[/cyan] -> 检测到强烈不满: [bold magenta]{dissatisfied_prob > 0.5}[/bold magenta] (概率: {dissatisfied_prob:.2f})"
        )
        print(
            "  ✅ 结论: 一次网络请求获取全部推测数据，无需等待二次来回即可直接派单换货。"
        )


def pattern_composite_scoring():
    """模式二：复合加权评分 (Composite Scoring)"""
    print()
    console.rule("[bold blue]模式二：复合加权评分 (Composite Scoring)[/bold blue]")
    print()

    client = get_typesafe_client()
    vip_feedback = "我们企业版下周即将上线大型促销活动，但目前发现批量导出报表经常 504 超时，这对我们非常致命！"

    console.print(
        Panel(vip_feedback, title="[blue]工单内容[/blue]", border_style="blue")
    )
    print("⏳ Jev 评估多维度细分指标（紧急度 + 业务影响面）...")

    response = client.system_one(
        state=vip_feedback,
        questions={
            "urgency": Noul(
                instructions="问题是否具备极强的时间紧急性（例如短期内有关键事件）？"
            ),
            "impact_scope": Score(
                instructions="评估故障对业务的影响范围",
                criteria=[
                    "仅个别非核心功能受影响，有临时替代方案",
                    "重要业务功能异常，影响部分正常运转",
                    "核心业务阻断或大范围不可用，可能造成重大损失",
                ],
            ),
        },
    )

    urgency_prob = response.answers["urgency"].noul
    impact_score = response.answers["impact_scope"].score  # 0.0 ~ 2.0

    # 业务层确定性加权计算公式：Priority = 紧急度 * 40 + 影响面(归一化) * 60
    impact_normalized = impact_score / 2.0
    composite_priority = (urgency_prob * 40) + (impact_normalized * 60)

    print()
    console.print(
        f"  • 维度一 (Noul 紧急度概率):   [yellow]{urgency_prob:.2f}[/yellow]"
    )
    console.print(
        f"  • 维度二 (Score 影响面得分):  [yellow]{impact_score:.1f} / 2.0[/yellow]"
    )
    console.print(
        f"  • 本地确定性加权算得优先级:   [bold cyan]{composite_priority:.1f} / 100[/bold cyan]"
    )

    print()
    if composite_priority >= 75:
        console.print(
            "  🚨 [bold red]动作决策: 综合优先级 >= 75，自动触发 P0 级即时告警并呼叫值班人员！[/bold red]"
        )


def pattern_confidence_escalation():
    """模式三：置信度与升级安全机制 (Confidence Escalation)"""
    print()
    console.rule(
        "[bold magenta]模式三：置信度与升级安全机制 (Confidence Escalation)[/bold magenta]"
    )
    print()

    client = get_typesafe_client()
    ambiguous_text = (
        "系统提示续费扣款成功了，但我看页面上依然写着体验版，这是怎么回事？"
    )

    console.print(
        Panel(
            ambiguous_text, title="[magenta]歧义输入[/magenta]", border_style="magenta"
        )
    )
    print("⏳ Jev 分析全概率分布与置信度集中度...")

    response = client.system_one(
        state=ambiguous_text,
        questions={
            "category": Choice(
                instructions="分类该咨询归属的专业组",
                criteria={
                    "billing": "扣费、账单与支付状态",
                    "account": "账号权限与套餐生效状态",
                    "tech": "技术 Bug 与页面渲染异常",
                },
            )
        },
    )

    category_answer = response.answers["category"]
    confidence = category_answer.confidence
    choice = category_answer.choice
    probs = category_answer.probabilities or {}

    print()
    console.print(f"  • 模型最高候选: [bold]{choice}[/bold]")
    console.print(f"  • 判定置信度:   [bold yellow]{confidence:.2f}[/bold yellow]")
    dist_str = ", ".join(f"{k}: {v:.2f}" for k, v in probs.items())
    console.print(f"  • 全概率分布:   [dim]{dist_str}[/dim]")

    # 护栏策略：当置信度低于 0.65 时，自动转人工工单排队，不直接路由
    THRESHOLD = 0.65
    print()
    if confidence < THRESHOLD:
        console.print(
            f"  ⚠️  [bold yellow]安全升级: 置信度低于预设阈值 {THRESHOLD}，说明属于多团队交叉的模糊边界，自动移交人工排队。[/bold yellow]"
        )
    else:
        console.print(
            f"  ✅ [bold green]置信度充足，直接自动分发至 {choice} 队列。[/bold green]"
        )
    print()


if __name__ == "__main__":
    pattern_fan_out()
    pattern_composite_scoring()
    pattern_confidence_escalation()
