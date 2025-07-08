# Calculator-MCP

High-precision calculator engine with a RESTful API **and** an [MCP](https://github.com/cascade-ai/mcp) server, built in Python.

---
## Features
• 34-digit decimal arithmetic via `decimal` & custom `EvalTransformer`  
• Trigonometric / log / power functions (see `calc_core/transformer.py`)  
• FastAPI HTTP endpoints – `/healthz`, `/evaluate`  
• MCP server exposing `calc.evaluate` function for AI agents  
• YAML-driven test cases

---
## Directory Layout
```
calculator-mcp/
├─ app/            # REST API (FastAPI)
├─ calc_core/      # Evaluation engine & grammar
├─ server/         # MCP server (FastAPI)
├─ documents/      # Design docs & specs
├─ tests/          # Pytest suites & YAML cases
└─ README.md       # ← you are here
```

---
## Prerequisites
* Python ≥ 3.11 (managed by [uv](https://github.com/astral-sh/uv))

Install `uv` once (if you haven’t):
```bash
pip install uv
```

---
## Setup
```bash
# Clone repo
 git clone https://github.com/your-org/calculator-mcp.git && cd calculator-mcp

# Install deps (creates .venv automatically)
uv pip install -r requirements.txt
```

If you add new deps, use:
```bash
uv add <package>  # e.g. uv add fastapi
```

---
## Running the REST API
```bash
uv run python -m uvicorn app.main:app --reload --port 8000
```
Open Swagger UI: <http://127.0.0.1:8000/docs>

Example request:
```bash
curl -X POST http://127.0.0.1:8000/evaluate \
     -H 'Content-Type: application/json' \
     -d '{"expr": "sin(pi/6) + 1"}'
```

---
## Running the MCP Server
```bash
uv run python -m uvicorn server.main:app --reload --port 9000
```
Invoke via HTTP:
```bash
curl -X POST http://127.0.0.1:9000/functions/calc.evaluate \
     -H 'Content-Type: application/json' \
     -d '{"expr": "1+2"}'
```
Expect: `{ "result": "3" }`

Refer to `documents/mcp_server_setup.md` for full details.

---
## Testing
```bash
uv pip install pytest httpx
uv run pytest -q
```

---
## Adding New Functions
1. Update `_FUNCS` or implement new handler in `calc_core/transformer.py`.  
2. Register with grammar if needed.  
3. For MCP, call `registry.add_function(...)` in `server/registry.py`.

---
## License
MIT
