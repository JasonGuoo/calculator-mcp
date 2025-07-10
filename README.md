# Calculator-MCP

> A high-precision, 34-digit calculator micro-service that you can drop into any LLM workflow. Exposes both a REST API **and** an [MCP](https://github.com/cascade-ai/mcp) server so that agents can evaluate expressions securely and deterministically.

---
## Supported Expressions

Calculator-MCP understands standard arithmetic along with a focused set of scientific functions and constants.

| Category | Syntax / Example |
|----------|-----------------|
| Addition / Subtraction | `1 + 2 - 3` |
| Multiplication / Division | `4 * 5 / 2` |
| Power | `2 ** 10` → `1024` |
| Parentheses & Unary +/- | `-(1 + 2) * 3` |
| Constants | `pi`, `e` |
| Trigonometric | `sin(pi/6)`, `cos(pi/3)`, `tan(pi/4)` |
| Inverse Trig | `asin(0.5)`, `acos(1)`, `atan(1)` |
| Logarithm | `log(8, 2)` (base optional; `log(10)` = ln) |
| Root & Power | `sqrt(2)`, `pow` via `**` |
| Exponential | `exp(1)` |
| Absolute Value | `abs(-3.5)` |

All calculations return a 34-digit‐precision `result` string.

---
## Why do I need this?

Large Language Models are notoriously poor at exact arithmetic—they may hallucinate numeric facts or return imprecise results. **Calculator-MCP** gives your agent a deterministic, 34-digit-precision oracle, ensuring every calculation is trustworthy and reproducible.

---
## Features
- 34-digit decimal arithmetic using Python `decimal`
- Standard math functions: trig, log, power, etc.
- REST endpoints: `POST /evaluate`, `GET /healthz`
- MCP function `calc.evaluate` ready for Function-Calling / Tool-Calling
- YAML-driven test suite and 100% typed codebase

---
## Quick Start

### Prerequisites
* Python ≥ 3.11 (managed with [uv](https://github.com/astral-sh/uv))

Install `uv` once (if you haven’t):
```bash
pip install uv
```

### Installation
```bash
git clone https://github.com/your-org/calculator-mcp.git
cd calculator-mcp
uv pip install -r requirements.txt   # creates .venv automatically
```

---
### Run the REST API
```bash
uv run python -m uvicorn app.main:app --reload --port 8000
# Swagger UI: http://127.0.0.1:8000/docs
```

### Run the MCP Server (HTTP)
```bash
uv run python -m uvicorn server.main:app --reload --port 9000
```
*Note: For direct tool integration (e.g., in Cursor), see the `stdio` server instructions below.*

---
## Integrating with a Large Language Model (LLM)

This project includes a complete, runnable example of how to integrate the calculator with an LLM-powered agent using the Model Context Protocol (MCP).

The agent uses the official `mcp` Python library to dynamically discover and call the calculator's functions based on natural language queries.

### How It Works

The example follows the official MCP `stdio` client pattern:

1.  **`stdio_server.py`**: A lightweight MCP server that communicates over standard input/output. It imports and exposes the core `calculate` function.
2.  **`examples/smart_calculator_agent.py`**: The client agent that launches the `stdio_server.py` as a subprocess. It uses OpenAI's GPT-4 to interpret user queries and the official `mcp` library to call the calculator tool when needed.

This separation ensures that the core calculator logic is independent of the server implementation (it can be run via HTTP or `stdio`).

### Running the Example

1.  **Set your OpenAI API Key**:

    Create a `.env` file in the root of the project and add your key:

    ```
    OPENAI_API_KEY="sk-..."
    ```

2.  **Run the agent**:

    Use `uv` to run the client script. The client will automatically start the `stdio` server.

    ```bash
    uv run python examples/smart_calculator_agent.py
    ```

### Example Code (`smart_calculator_agent.py`)

The full source code for the agent is available in the `examples` directory. It demonstrates how to launch the `stdio` server and interact with the LLM.

[**View the agent source code (`smart_calculator_agent.py`)**](./examples/smart_calculator_agent.py)

---

## Using with MCP-Compatible Tools (e.g., Cursor)

You can integrate this calculator directly into any MCP-compatible client, like Cursor, by creating a `.cursor/mcp.json` file in your project's root directory. This file tells Cursor how to find and communicate with your tool.

### Method 1: Connecting to the Running HTTP Server (Recommended)

This method is for when you have the MCP server running and want to connect to it from Cursor.

1.  **Start the MCP Server**: First, ensure the spec-compliant JSON-RPC server is running.
    ```bash
    uv run python -m uvicorn server.main:app --reload --port 9000
    ```

2.  **Configure Cursor**:
    *   In your project, create a file named `.cursor/mcp.json`.
    *   Add the following JSON configuration. This tells Cursor that your server is available at the specified URL and speaks the standard MCP protocol.
      ```json
      {
        "mcpServers": {
          "calculator": {
            "url": "http://127.0.0.1:9000"
          }
        }
      }
      ```
    *   Save the file. Cursor will automatically detect it, send a `tools/list` request to the server, and make the `calc.evaluate` tool available to the AI.

### Method 2: Running as a Local Stdio Tool

This alternative method is useful if you don't want to manage a separate server process. Cursor will start and stop the tool on demand using standard input/output.

1.  **Configure Cursor**:
    *   In your project, create a file named `.cursor/mcp.json`.
    *   Add the following JSON configuration to the file:
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
    *   Save the file. Cursor will run the `stdio_server.py` script in the background to make the `calculate` function available to the AI.

---
## Testing
```bash
uv run pytest -q
```

---
## License
MIT
