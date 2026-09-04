# Hello Agents

用于学习与探索 AI Agent 开发基础与实践的 Python 项目。

## 🛠️ 环境要求

- Python >= 3.12
- 推荐使用 [uv](https://github.com/astral-sh/uv) 进行依赖和虚拟环境管理

## 🚀 快速上手

### 1. 安装依赖

使用 `uv` 同步项目依赖：

```bash
uv sync
```

## 💻 VS Code 推荐开发配置

为了获得流畅舒适的 Python 开发体验，推荐安装以下 VS Code 扩展：

- **Python** (`ms-python.python`)
- **Pylance** (`ms-python.vscode-pylance`)：提供高效的代码索引、补全与类型检查
- **Ruff** (`charliermarsh.ruff`)：极速的代码分析与格式化工具

在项目根目录的 `.vscode/settings.json` 中添加如下配置：

```json
{
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit"
        }
    },

    // 自动 Import
    "python.analysis.autoImportCompletions": true,

    // Python 自动缩进
    "python.analysis.autoIndent": true,

    // 输入字符串表达式时自动转 f-string
    "python.analysis.autoFormatStrings": true,

    "python.analysis.indexing": true,
    "python.analysis.autoSearchPaths": true,
    "python.analysis.diagnosticMode": "workspace",

    "python.analysis.typeCheckingMode": "standard",

    "ruff.lint.ignore": [
        "BLE001"
    ]
}
```

## 📝 开发与学习计划

- [ ] Agent 基础概念与提示词工程（Prompt Engineering）
- [ ] 基于 LLM API 的单 Agent 交互
- [ ] 工具调用与函数调用（Tool Calling / Function Calling）
- [ ] 内存与上下文管理（Memory & State）
- [ ] 多 Agent 协作与工作流编排

