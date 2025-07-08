# Building an MCP Server for Calculator-MCP

This guide explains how to expose *calculator-mcp* as a **Model Context Protocol** (MCP) server so that external AI agents (e.g. Cascade) can discover and invoke high-precision evaluation capabilities programmatically.

---
## 1. MCP Primer
MCP standardises how tools (functions) and data (resources) are advertised over a simple HTTP+JSON interface:

* **list_resources** – enumerate available objects/functions ‑ supports pagination via cursor.
* **read_resource** – retrieve the contents/metadata of a single resource.
* **Custom function endpoints** – prefixed with `functions/`, registered under `namespace.function_name` (mirrors the schema in agent tool prompts).

> See the [MCP specification](https://github.com/cascade-ai/mcp/blob/main/SPEC.md) for wire-level details.

---
## 2. High-level Architecture
```
calculator-mcp/
├─ server/                 # new package hosting MCP server
│  ├─ __init__.py
│  ├─ main.py              # FastAPI app exposing MCP endpoints
│  ├─ schemas.py           # Pydantic models shared across endpoints
│  └─ registry.py          # Central registry of resources & functions
└─ calc_core/              # existing evaluation engine
```
We leverage **FastAPI** (already chosen for REST API) to serve MCP routes as well.

---
## 3. Dependencies
Add (if not present) to `requirements.txt` or `pyproject.toml`:
```
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
python-multipart>=0.0.9   # if file upload resources later
```
Install via:
```bash
uv pip install -r requirements.txt
```

---
## 4. Implementing the Registry (`server/registry.py`)
```python
from typing import Any, Dict, List, Optional

from calc_core.transformer import EvalTransformer, CalcError, CTX

class ResourceRegistry:
    """Keeps track of resources & function metadata for MCP discovery."""

    def __init__(self):
        self._resources: Dict[str, Dict[str, Any]] = {}
        self._functions: Dict[str, Dict[str, Any]] = {}

    # ---------- resources ----------
    def add_resource(self, uri: str, meta: Dict[str, Any]):
        self._resources[uri] = meta

    def list_resources(self, cursor: Optional[str] = None, limit: int = 50):
        items = list(self._resources.items())
        start = int(cursor) if cursor else 0
        end = start + limit
        next_cursor = str(end) if end < len(items) else None
        return items[start:end], next_cursor

    def get_resource(self, uri: str):
        return self._resources.get(uri)

    # ---------- functions ----------
    def add_function(self, name: str, meta: Dict[str, Any]):
        self._functions[name] = meta

    def list_functions(self):
        return self._functions

registry = ResourceRegistry()

# Register default high-precision evaluate function
def _evaluate(expr: str, variables: dict | None = None):
    try:
        from calc_core.parser import parse
        t = EvalTransformer(variables)
        return str(parse(expr, t))
    except CalcError as e:
        raise ValueError(str(e))

registry.add_function(
    "calc.evaluate",
    {
        "description": "Evaluate a math expression with 34-digit precision.",
        "parameters": {
            "expr": "string",
            "variables": "dict (optional)"
        },
        "handler": _evaluate,
    },
)
```

---
## 5. FastAPI Entrypoint (`server/main.py`)
```python
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .registry import registry

app = FastAPI(title="Calculator-MCP Server", version="1.0.0")

# ---------- MCP standard routes ----------
@app.get("/list_resources")
async def list_resources(cursor: str | None = None):
    items, next_cursor = registry.list_resources(cursor)
    return {"items": [dict(uri=k, **v) for k, v in items], "next_cursor": next_cursor}

@app.get("/read_resource")
async def read_resource(uri: str):
    res = registry.get_resource(uri)
    if res is None:
        raise HTTPException(404, detail="Resource not found")
    return res

# ---------- dynamic function invocation ----------
@app.post("/functions/{ns}.{fn}")
async def call_function(ns: str, fn: str, body: Dict[str, Any]):
    name = f"{ns}.{fn}"
    meta = registry.list_functions().get(name)
    if meta is None:
        raise HTTPException(404, detail="Function not found")
    try:
        result = meta["handler"](**body)
        return JSONResponse(content={"result": result})
    except Exception as exc:
        raise HTTPException(400, detail=str(exc))
```

---
## 6. Running Locally
```bash
uv run python -m uvicorn server.main:app --reload --port 9000
```
You can now test with `curl`:
```bash
curl -X POST http://127.0.0.1:9000/functions/calc.evaluate \
     -H 'Content-Type: application/json' \
     -d '{"expr": "sin(pi/4)^2 + cos(pi/4)^2"}'
```
Expect response:
```json
{"result": "1"}
```

---
## 7. Integration with Agents
In Cascade tool manifest, you would declare:
```jsonc
{
  "namespace": "calc",
  "endpoint": "http://your-host:9000/functions/{name}",
  "functions": [
    {
      "name": "evaluate",
      "description": "Evaluate expression…",
      "parameters_schema": {"type": "object", "properties": {"expr": {"type": "string"}, "variables": {"type": "object"}}}
    }
  ]
}
```

---
## 8. Production Deployment
1. **Docker** – create a lightweight image with `uvicorn[standard]`. Example `Dockerfile`:
    ```dockerfile
    FROM python:3.11-slim
    WORKDIR /app
    COPY . .
    RUN pip install --no-cache-dir fastapi uvicorn[standard]
    CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "9000"]
    ```
2. **Reverse proxy** – place Nginx or Traefik for TLS termination.
3. **Observability** – add OpenTelemetry middleware for traces/metrics.

---
## 9. Further Enhancements
* Pagination & filtering for large resource sets.
* Auth (API keys, OAuth2) on MCP routes.
* Streaming responses for long-running calculations.
* Function versioning (`calc.evaluate.v2`).

---
© 2025 Calculator-MCP
