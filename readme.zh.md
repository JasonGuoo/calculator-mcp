# 计算器-MCP (Calculator-MCP)

> 一个高精度的34位计算器微服务，您可以轻松集成到任何大型语言模型（LLM）工作流中。它同时提供 REST API 和 [MCP](https://github.com/cascade-ai/mcp) 服务器，使智能体能够安全、确定地评估数学表达式。

---
## 支持的表达式

Calculator-MCP 支持标准算术运算以及一系列科学函数和常量。

| 类别 | 语法 / 示例 |
|----------|-----------------|
| 加法 / 减法 | `1 + 2 - 3` |
| 乘法 / 除法 | `4 * 5 / 2` |
| 幂运算 | `2 ** 10` → `1024` |
| 括号 & 一元 +/- | `-(1 + 2) * 3` |
| 常量 | `pi`, `e` |
| 三角函数 | `sin(pi/6)`, `cos(pi/3)`, `tan(pi/4)` |
| 反三角函数 | `asin(0.5)`, `acos(1)`, `atan(1)` |
| 对数 | `log(8, 2)` (底数可选; `log(10)` = ln) |
| 平方根 & 幂 | `sqrt(2)`, `pow` 通过 `**` 实现 |
| 指数函数 | `exp(1)` |
| 绝对值 | `abs(-3.5)` |

所有计算均返回一个34位精度的 `result` 字符串。

---
## 为什么我需要这个？

众所周知，大型语言模型在精确算术方面表现不佳——它们可能会产生数字幻觉或返回不精确的结果。**Calculator-MCP** 为您的智能体提供了一个确定性的、34位精度的计算“神谕”，确保每次计算都值得信赖且可复现。

---
## 功能特性
- 使用 Python `decimal` 实现34位十进制算术
- 标准数学函数：三角、对数、幂等
- REST 端点：`POST /evaluate`, `GET /healthz`
- MCP 函数 `calc.evaluate` 已为函数调用/工具调用准备就绪
- YAML驱动的测试套件和100%类型化的代码库

---
## 快速入门

### 先决条件
* Python ≥ 3.11 (使用 [uv](https://github.com/astral-sh/uv) 管理)

如果您尚未安装 `uv`，请先安装：
```bash
pip install uv
```

### 安装
```bash
git clone https://github.com/your-org/calculator-mcp.git
cd calculator-mcp
uv pip install -r requirements.txt   # 自动创建 .venv
```

---
### 运行 REST API
```bash
uv run python -m uvicorn app.main:app --reload --port 8000
# Swagger UI 界面: http://127.0.0.1:8000/docs
```

### 运行 MCP 服务器 (HTTP)
```bash
uv run python -m uvicorn server.main:app --reload --port 9000
```
*注意：对于直接的工具集成（例如在 Cursor 中），请参阅下方的 `stdio` 服务器说明。*

---
## 与大型语言模型 (LLM) 集成

本项目包含一个完整的、可运行的示例，演示了如何使用模型上下文协议 (MCP) 将计算器与由 LLM 驱动的智能体集成。

该智能体使用官方的 `mcp` Python 库，根据自然语言查询动态发现并调用计算器的函数。

### 工作原理

该示例遵循官方的 MCP `stdio` 客户端模式：

1.  **`stdio_server.py`**: 一个通过标准输入/输出进行通信的轻量级 MCP 服务器。它导入并暴露了核心的 `calculate` 函数。
2.  **`examples/smart_calculator_agent.py`**: 启动 `stdio_server.py` 作为子进程的客户端智能体。它使用 OpenAI 的 GPT-4 来解释用户查询，并使用官方的 `mcp` 库在需要时调用计算器工具。

这种分离确保了核心计算器逻辑独立于服务器实现（它可以通过 HTTP 或 `stdio` 运行）。

### 运行示例

1.  **设置您的 OpenAI API 密钥**：

    在项目根目录下创建一个 `.env` 文件，并添加您的密钥：

    ```
    OPENAI_API_KEY="sk-..."
    ```

2.  **运行智能体**：

    使用 `uv` 运行客户端脚本。客户端将自动启动 `stdio` 服务器。

    ```bash
    uv run python examples/smart_calculator_agent.py
    ```

### 示例代码 (`smart_calculator_agent.py`)

智能体的完整源代码可在 `examples` 目录中找到。它演示了如何启动 `stdio` 服务器并与 LLM 互动。

[**查看智能体源代码 (`smart_calculator_agent.py`)**](./examples/smart_calculator_agent.py)

---

## 在兼容 MCP 的工具中使用 (例如 Cursor)

您可以通过在项目根目录中创建一个 `.cursor/mcp.json` 文件，将此计算器直接集成到任何兼容 MCP 的客户端（如 Cursor）中。该文件告诉 Cursor 如何查找并与您的工具通信。

### 方法 1：连接到正在运行的 HTTP 服务器 (推荐)

当您已经运行了 MCP 服务器并希望从 Cursor 连接到它时，请使用此方法。

1.  **启动 MCP 服务器**：首先，确保符合规范的 JSON-RPC 服务器正在运行。
    ```bash
    uv run python -m uvicorn server.main:app --reload --port 9000
    ```

2.  **配置 Cursor**：
    *   在您的项目中，创建一个名为 `.cursor/mcp.json` 的文件。
    *   添加以下 JSON 配置。这告诉 Cursor 您的服务器在指定的 URL 上可用，并使用标准的 MCP 协议。
      ```json
      {
        "mcpServers": {
          "calculator": {
            "url": "http://127.0.0.1:9000"
          }
        }
      }
      ```
    *   保存文件。Cursor 将自动检测到它，向服务器发送 `tools/list` 请求，并使 `calc.evaluate` 工具可供 AI 使用。

### 方法 2：作为本地 Stdio 工具运行

如果您不想管理一个单独的服务器进程，这种替代方法很有用。Cursor 将按需使用标准输入/输出来启动和停止该工具。

1.  **配置 Cursor**：
    *   在您的项目中，创建一个名为 `.cursor/mcp.json` 的文件。
    *   将以下 JSON 配置添加到文件中：
      ```json
      {
        "mcpServers": {
          "calculator": {
            "command": "uv",
            "args": ["run", "python", "stdio_server.py"],
            "cwd": "${workspaceFolder}"
          }
        }
      }
      ```
    *   保存文件。Cursor 将在后台运行 `stdio_server.py` 脚本，使 `calculate` 函数可供 AI 使用。

---
## 测试
```bash
uv run pytest -q
```

---
## 许可证
MIT
