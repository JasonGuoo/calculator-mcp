from __future__ import annotations

"""FastAPI application exposing MCP-compatible endpoints."""

from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .registry import registry

app = FastAPI(title="Calculator MCP Server", version="1.0.0")

# ---------------------------------------------------------------------
# MCP standard endpoints
# ---------------------------------------------------------------------


@app.get("/list_resources")
async def list_resources(cursor: str | None = None):
    items, next_cursor = registry.list_resources(cursor)
    return {"items": [{"uri": k, **v} for k, v in items], "next_cursor": next_cursor}


@app.get("/read_resource")
async def read_resource(uri: str):
    res = registry.get_resource(uri)
    if res is None:
        raise HTTPException(404, detail="Resource not found")
    return res


# ---------------------------------------------------------------------
# Dynamic function invocation
# ---------------------------------------------------------------------


@app.post("/functions/{namespace}.{func_name}")
async def call_function(namespace: str, func_name: str, body: Dict[str, Any]):
    full_name = f"{namespace}.{func_name}"
    meta = registry.get_function(full_name)
    if meta is None:
        raise HTTPException(404, detail="Function not found")
    handler = meta["handler"]
    try:
        result = handler(**body)
        return JSONResponse(content={"result": result})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, detail=str(exc)) from exc
