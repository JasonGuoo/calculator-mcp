from __future__ import annotations

"""FastAPI application exposing calculator evaluate endpoint."""

from decimal import getcontext

from fastapi import FastAPI, HTTPException

from calc_core.transformer import EvalTransformer, CalcError
from calc_core.parser import PARSER
from .schemas import EvaluateRequest, EvaluateResponse

app = FastAPI(title="Calculator-MCP REST API", version="1.0.0")


@app.get("/healthz")
async def healthz():
    """Liveness/readiness probe."""

    return {"status": "ok"}


@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest):
    """Evaluate an expression and return high-precision result."""

    try:
        transformer = EvalTransformer(req.variables)
        tree = PARSER.parse(req.expr)
        result = transformer.transform(tree)  # type: ignore[arg-type]
        return EvaluateResponse(result=str(result), precision=getcontext().prec)
    except CalcError as ce:
        raise HTTPException(status_code=400, detail=str(ce))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid expression") from exc
