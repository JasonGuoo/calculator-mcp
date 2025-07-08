# Calculator API Design (FastAPI)

This document outlines the public HTTP API for the *calculator-mcp* service, along with concrete implementation guidelines using **FastAPI**.

---
## 1. Base URL

Assuming the service is deployed locally:
```
http://127.0.0.1:8000
```

In production, replace the host/port accordingly.

---
## 2. Endpoints

| Method | Path          | Purpose                       |
| ------ | ------------- | ----------------------------- |
| GET    | `/healthz`    | Liveness / readiness check    |
| POST   | `/evaluate`   | Evaluate a mathematical expression and return a high-precision result |

### 2.1 `GET /healthz`
Simple probe used by load-balancers and k8s.
```
Response: 200 OK 
Body: {"status": "ok"}
```

### 2.2 `POST /evaluate`
Evaluate an arithmetic expression with optional user-supplied variables.

Request JSON schema (Pydantic model `EvaluateRequest`):
```jsonc
{
  "expr": "sin(pi/6) + x * 3",      // required, string
  "variables": {                     // optional, key-value map
    "x": 1.2345,
    "y": "2e-3"
  }
}
```
• `expr`: Lark-compatible expression understood by `calc_core.transformer.EvalTransformer`.
• `variables`: Each value is cast to `decimal.Decimal` via `Decimal(str(v))`.

Successful response (model `EvaluateResponse`):
```jsonc
{
  "result": "2.734500000000000...",  // string for arbitrary precision
  "precision": 34                      // current decimal context precision
}
```

Error responses use RFC 7807 style (FastAPI default):
* **400 Bad Request** – syntax error, division by zero, domain error, etc. (raised as `CalcError`).
* **422 Unprocessable Entity** – invalid JSON/body.

---
## 3. Implementation Guide

### 3.1 Project layout additions
```
calculator-mcp/
├─ app/
│  ├─ __init__.py         # empty, marks as package
│  ├─ main.py             # FastAPI application instance
│  └─ schemas.py          # Pydantic request/response models
└─ documents/
   └─ api_design.md       # ← (this file)
```

### 3.2 Dependencies
Add to `pyproject.toml` / `requirements.txt`:
```
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
```
(Install via `uv pip install -r requirements.txt`).

### 3.3 Code snippets

`app/schemas.py`
```python
from decimal import Decimal
from typing import Dict, Optional

from pydantic import BaseModel, Field, condecimal

class EvaluateRequest(BaseModel):
    expr: str = Field(..., description="Expression to evaluate")
    variables: Optional[Dict[str, condecimal(max_digits=40)]] = None

class EvaluateResponse(BaseModel):
    result: str
    precision: int
```

`app/main.py`
```python
from decimal import getcontext

from fastapi import FastAPI, HTTPException

from calc_core.transformer import EvalTransformer, CalcError, CTX
from .schemas import EvaluateRequest, EvaluateResponse

app = FastAPI(title="Calculator-MCP API", version="1.0.0")

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest):
    try:
        transformer = EvalTransformer(req.variables)
        # The parser utility is assumed to live in calc_core (not shown here)
        from calc_core.parser import parse  # ← create thin wrapper around Lark
        result = parse(req.expr, transformer)
        return EvaluateResponse(result=str(result), precision=getcontext().prec)
    except CalcError as ce:
        raise HTTPException(status_code=400, detail=str(ce))
```

> **Note**: If a dedicated `parse()` helper is not yet available, you can integrate Lark inside the endpoint or expose a wrapper in `calc_core.__init__`.

### 3.4 Running locally
```bash
uv run python -m uvicorn app.main:app --reload
```
(UV ensures the virtual environment and dependencies are isolated per the project’s `pyproject.toml`.)

### 3.5 Testing
Use the built-in Swagger UI at `/docs` or `pytest` with `httpx` client:
```python
from httpx import AsyncClient
from app.main import app

async def test_eval():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post("/evaluate", json={"expr": "1+2"})
    assert res.json()["result"] == "3"
```

---
## 4. Future Extensions
1. **Authentication** – e.g., API keys or JWT.

---
© 2025 Calculator-MCP
