"""Jev 核心三大判断原语（Primitives）教学

架构设计说明（贯彻 python-design-patterns 原则）：
1. 关注点分离（Separation of Concerns）：
   - 业务感知：analyze_ticket() 纯粹负责调用 Jev 提取三原语数据，无打印污染。
   - 业务决策：make_decision() 纯粹负责基于连续概率做出业务决策计划，无打印污染。
   - 结果呈现：render_dashboard() 独立负责自解释、可视化的终端仪表盘渲染。
2. 概率直观化：
   - 将 Choice 的竞争分布转化为直观的横向对比进度条。
   - 将 Noul 的连续概率展示为概率仪表盘（非绝对布尔值）。
   - 将 Score 的阶梯分值清晰映射到业务阶段阶段锚点。
"""

from dataclasses import dataclass

from client import get_typesafe_client
from rich.console import Console
from rich.panel import Panel
from typesafe_sdk import (
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Score,
    ScoreAnswer,
    TypeSafeClient,
)

console = Console()


# ==========================================
# 1. 领域模型定义 (Domain Models)
# ==========================================


@dataclass
class TicketInsights:
    """Jev 结构化感知输出"""

    handler: ChoiceAnswer  # Choice 原语：多意图竞争与分布
    close_prob: NoulAnswer  # Noul 原语：成单概率（校准连续值）
    stage: ScoreAnswer  # Score 原语：推进阶段分值


@dataclass
class DecisionPlan:
    """基于概率生成的下游业务动作计划"""

    dispatch_mode: str  # 派发策略（单向派发 / 双向协同）
    primary_owner: str  # 主牵头人
    collaborator: str | None  # 协同人
    dispatch_reason: str  # 派发决策理由
    lead_tier: str  # CRM 线索评级
    action_trigger: str  # 触发的业务动作


# ==========================================
# 2. 核心业务逻辑 (Business Workflow)
# ==========================================


def analyze_ticket(client: TypeSafeClient, ticket_text: str) -> TicketInsights:
    """【业务步骤 1】调用 Jev 获取三原语感知数据（纯粹的分析计算，不含任何打印语句）"""
    response = client.system_one(
        state=ticket_text,
        questions={
            "handler": Choice(
                instructions="判定该工单由哪个专业部门牵头处理",
                criteria={
                    "sales_rep": "销售商务：负责价格谈判、方案报价与成本答疑",
                    "technical_support": "技术支持：负责排查 502 报错与性能压测排障",
                },
            ),
            "will_close": Noul(
                instructions="该客户是否具备短期内顺利签约的高概率成单特征？",
            ),
            "deal_stage": Score(
                instructions="评估客户当前所处的采购决策推进阶段",
                criteria=[
                    "方案评估：技术初步摸索，尚未提实质性商务采购前提",
                    "意向谈判：有明确采购意愿，但提出具体附加条件（折扣/技术验收）",
                    "合同流程：已确定采购方案，进入最终法务与付款流程",
                ],
            ),
        },
    )
    return TicketInsights(
        handler=response.answers["handler"],
        close_prob=response.answers["will_close"],
        stage=response.answers["deal_stage"],
    )


def make_decision(insights: TicketInsights) -> DecisionPlan:
    """【业务步骤 2】基于连续概率做确定性规则裁决（纯粹的决策逻辑，无打印污染）"""
    probs = insights.handler.probabilities or {}
    sales_p = probs.get("sales_rep", 0.0)
    tech_p = probs.get("technical_support", 0.0)

    # 决策 1：利用 Choice 全概率分布，判定是否触发双团队协同
    # 只要次要诉求具备实质概率（>= 10%），即触发跨部门协同，避免传统硬分类直接丢弃次要意图
    minor_p = min(sales_p, tech_p)
    if minor_p >= 0.10:
        dispatch_mode = "双向协同派发 (Cross-functional Handshake)"
        if tech_p >= sales_p:
            primary_owner = "技术支持部"
            collaborator = "大客户销售部 (商务折扣洽谈)"
        else:
            primary_owner = "大客户销售部"
            collaborator = "技术支持部 (502故障排查)"

        dispatch_reason = (
            f"主诉求为 {primary_owner} ({max(sales_p, tech_p) * 100:.0f}%)，"
            f"但伴随显著的协同诉求 ({collaborator.split()[0]} {minor_p * 100:.0f}%)，单一派发将遗漏关键诉求"
        )
    else:
        dispatch_mode = "单一部门直接派单"
        primary_owner = "大客户销售部" if sales_p > tech_p else "技术支持部"
        collaborator = None
        dispatch_reason = f"{primary_owner} 意图形成绝对压倒性优势 (>= 90%)"

    # 决策 2：利用 Noul 浮点胜率，决定 CRM 运营策略
    win_rate = insights.close_prob.noul
    if win_rate >= 0.70:
        lead_tier = "A 级 (高确定性赢单)"
        action_trigger = "直接排入当季重点业绩预测，按标准流程签约"
    elif 0.30 <= win_rate < 0.70:
        lead_tier = "B 级 (高潜力攻坚客户)"
        action_trigger = "申请特批折扣方案 (挽留成本犹豫) + 资深技术 24h 兜底修复 502"
    else:
        lead_tier = "C 级 (早期低意向观望)"
        action_trigger = "转入常规营销内容自动化培育"

    return DecisionPlan(
        dispatch_mode=dispatch_mode,
        primary_owner=primary_owner,
        collaborator=collaborator,
        dispatch_reason=dispatch_reason,
        lead_tier=lead_tier,
        action_trigger=action_trigger,
    )


# ==========================================
# 3. 表现层：自解释可视化仪表盘 (Presentation)
# ==========================================


def _render_bar(prob: float, length: int = 20, color: str = "cyan") -> str:
    """生成字符进度条"""
    filled = round(prob * length)
    empty = length - filled
    return f"[{color}]{'█' * filled}{'░' * empty}[/{color}] {prob * 100:4.1f}%"


def render_dashboard(ticket_text: str, insights: TicketInsights, plan: DecisionPlan):
    """【表现层】渲染自解释的工单智能分析与决策仪表盘"""
    print()
    console.rule("[bold cyan]Jev 概率感知与业务弹性响应仪表盘[/bold cyan]")
    print()

    # 模块 1：原始输入
    console.print(
        Panel(
            f"[bold white]{ticket_text}[/bold white]",
            title="[bold blue]1. 客户工单原声 (Customer Voice)[/bold blue]",
            subtitle="[dim]多意图交织：同时包含 502 技术报错与商务折扣犹豫[/dim]",
            border_style="blue",
            padding=(1, 2),
        )
    )
    print()

    # 模块 2：Jev 三原语感知数据（可视化概率透镜）
    probs = insights.handler.probabilities or {}
    sales_p = probs.get("sales_rep", 0.0)
    tech_p = probs.get("technical_support", 0.0)

    stage_score = insights.stage.score
    stage_desc = (
        "意向谈判期 (提出具体折扣/验收前提)"
        if 0.5 <= stage_score < 1.5
        else "初探期或合同期"
    )

    lens_content = (
        "[bold magenta]▶ [Choice] 诉求意图分布 (Intent Distribution)[/bold magenta]\n"
        f"  • 销售商务意图: {_render_bar(sales_p, 16, 'cyan')}\n"
        f"  • 技术排障意图: {_render_bar(tech_p, 16, 'yellow')}\n"
        f"  [dim]↳ 语义透析: 两方意图竞争激烈，置信度降至 [bold yellow]{insights.handler.confidence:.2f}[/bold yellow]（若按传统单选只会强制挑一个，必然遗漏另一方核心诉求）[/dim]\n\n"
        "[bold magenta]▶ [Noul] 预期成单胜率 (Calibrated Win-Rate)[/bold magenta]\n"
        f"  • 成交可能性:   {_render_bar(insights.close_prob.noul, 16, 'green')}\n"
        "  [dim]↳ 语义透析: 落在 30%~70% 的关键攻坚灰度带，校准概率明确指出：客户有强烈意向，但面临成本与技术双重障碍[/dim]\n\n"
        "[bold magenta]▶ [Score] 采购推进阶段 (Deal Stage Rubric)[/bold magenta]\n"
        f"  • 阶段定级得分: [bold green]{stage_score:.2f} / 2.0[/bold green] (置信度: {insights.stage.confidence:.2f})\n"
        f"  [dim]↳ 语义透析: 精准锚定在【{stage_desc}】，客户已经明确'只要满足折扣且技术过关就签约'[/dim]"
    )

    console.print(
        Panel(
            lens_content,
            title="[bold green]2. Jev 概率感知透镜 (Probability Insights)[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )
    print()

    # 模块 3：下游业务响应动作
    action_content = (
        f"[bold yellow]▶ 动作一：工单智能路由[/bold yellow] -> [bold green]{plan.dispatch_mode}[/bold green]\n"
        f"  • 主牵头团队: [bold cyan]{plan.primary_owner}[/bold cyan]\n"
        f"  • 协同跟进人: [bold yellow]{plan.collaborator}[/bold yellow]\n"
        f"  • 决策依据:   {plan.dispatch_reason}\n\n"
        f"[bold yellow]▶ 动作二：CRM 销售漏斗评级[/bold yellow] -> [bold yellow]{plan.lead_tier}[/bold yellow]\n"
        f"  • 自动化运营: {plan.action_trigger}"
    )

    console.print(
        Panel(
            action_content,
            title="[bold yellow]3. 连续概率驱动的确定性业务响应 (Automated Execution)[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
    )

    print()
    console.rule("[dim]全流程执行完毕 · 代码逻辑与呈现解耦[/dim]")
    print()


if __name__ == "__main__":
    sample_ticket = (
        "我们团队正在测试企业版，意向挺高但领导还在犹豫成本。"
        "另外今天压测时遇到了 502 报错，麻烦工程师给看看。"
        "如果下周技术没问题且能给个折扣，我们就拍板签约。"
    )

    # 步骤 1：获取客户端并进行 Jev 感知分析
    client = get_typesafe_client()
    insights = analyze_ticket(client, sample_ticket)

    # 步骤 2：业务代码消费概率，生成行动计划
    decision = make_decision(insights)

    # 步骤 3：渲染可视化仪表盘
    render_dashboard(sample_ticket, insights, decision)
