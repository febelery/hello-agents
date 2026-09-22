# Chapter 5: TypeSafe Jev 快慢双系统 Agent 协同实战

本章聚焦于 **TypeSafe Jev（System One 模型）** 与 **大语言模型（System Two 慢思考）** 的架构协同。通过应用 Python 核心设计原则（KISS、单一职责、关注点分离、组合优于继承、依赖注入），打造高内聚、低延迟、可测试的现代化 Agent 架构。

---

## 1. 核心架构理念：快慢双系统 (Dual-System)

传统的 Agent 往往将所有语义理解、安全拦截、路由分类和业务处理全部交给昂贵的大语言模型（LLM），带来了高延迟、高成本和不稳定概率。

本章引入 **System One (快决策) + System Two (慢思考)** 的协同分工：

```
                    ┌───────────────────────────────┐
                    │      用户请求 (User Input)     │
                    └──────────────┬────────────────┘
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────────┐
        │  System 1: TypeSafe Jev (毫秒级结构化确定性判断)        │
        ├──────────────────────────────────────────────────────┤
        │  1. ContentGuardrail: 越狱与提示词注入拦截 (Noul/Score) │
        │  2. SemanticRouter: 语义分支路由 (Choice)            │
        └──────────────┬───────────────────────┬───────────────┘
                       │                       │
      [轻量/闲聊/违规分支]                      │ [需要复杂生成/代码任务]
                       │                       │
                       ▼                       ▼
            ┌─────────────────────┐  ┌───────────────────────────────────┐
            │ 本地 Handler 直接响应 │  │ System 2: OpenRouter 免费大模型   │
            │ (0 延迟、0 Token 开销)│  │ (深度生成高质量专业答复)          │
            └─────────────────────┘  └───────────────────────────────────┘
```

---

## 2. 目录架构与设计模式落地

本项目严格遵循 `python-design-patterns` 原则，杜绝冗余的深层目录嵌套与繁琐数字前缀：

```text
chapter5/
├── README.md               # 本章导读与设计说明
├── client.py               # 基础设施层：单点管理凭证与 Client 实例化（KISS）
├── primitives.py           # 原语篇：Choice、Noul、Score 三大原语的基本用法与对比
├── patterns.py             # 模式篇：并发展开（Fan-out）、复合加权（Composite Scoring）、置信度降级
├── router.py               # 组件篇：语义路由器（单一职责原则 SRP）
├── guardrail.py            # 组件篇：输入安全合规护栏（单一职责原则 SRP）
├── agent.py                # 实战篇：快慢协同 Agent（组合优于继承、依赖注入）
└── jev.py                  # 基础连通性最小验证脚本
```

### 设计原则对照

| 设计原则 | 对应代码与实现 |
|---|---|
| **KISS (保持简单)** | 路由器分发直接使用 Python 原生字典表；原语调用不增加多余装饰器封装。 |
| **SRP (单一职责)** | `router.py` 仅关注路由分发；`guardrail.py` 仅关注安全与合规审查；二者互不耦合。 |
| **SoC (关注点分离)** | 配置与网络（`client.py`）、判断组件（`router`/`guardrail`）、编排（`agent.py`）分层清晰。 |
| **组合优于继承** | `DualSystemAgent` 组合了 Guardrail、Router 与 LLM，而不是多继承庞大基类。 |
| **依赖注入 (DI)** | 各组件均通过 `__init__(client=...)` 接收外部依赖，便于单测替换与 Mock。 |


---

## 3. 运行与学习指南

本章节所有脚本均可使用 `uv run` 独立执行：

### 3.1 核心原语快速体验 (`primitives.py`)
观察 `Choice`（单选）、`Noul`（命题概率）、`Score`（序数标尺）在同一工单上的输出：
```bash
uv run python chapter5/primitives.py
```

### 3.2 Jev 核心架构模式 (`patterns.py`)
学习并发展开（Speculative Fan-out）、确定性复合加权评分以及置信度阈值降级：
```bash
uv run python chapter5/patterns.py
```

### 3.3 独立组件调试
验证单一职责的路由器与安全合规护栏：
```bash
# 测试语义路由器
uv run python chapter5/router.py

# 测试越狱与提示词注入拦截护栏
uv run python chapter5/guardrail.py
```

### 3.4 完整双系统协同实战 (`agent.py`)
体验 Jev 毫秒级护栏 + 路由分流与 OpenRouter 免费模型的无缝协同：
```bash
uv run python chapter5/agent.py
```
