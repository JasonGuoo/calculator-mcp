from __future__ import annotations

"""FastAPI application exposing a spec-compliant MCP server."""

import logging
from typing import Any, Dict

import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from .registry import registry, CalcError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Calculator MCP Server", version="1.0.0")


def json_rpc_response(request_id: int | str, result: Any) -> Dict[str, Any]:
    """Construct a successful JSON-RPC response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def json_rpc_error(request_id: int | str, code: int, message: str) -> Dict[str, Any]:
    """Construct a JSON-RPC error response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


@app.post("/")
async def mcp_rpc_handler(request: Request):
    """Handles all incoming MCP JSON-RPC requests."""
    logger.info(f"Received request on {request.url.path}")
    try:
        body = await request.json()
        logger.info(f"MCP-REQUEST-BODY: {body}")

        def create_and_log_response(content, status_code=200):
            logger.info(f"MCP-RESPONSE-BODY: {content}")
            return JSONResponse(status_code=status_code, content=content)

        request_id = body.get("id")
        method = body.get("method")
        params = body.get("params", {})

        # Handle notifications (requests without an id)
        if request_id is None:
            if method == "notifications/initialized":
                # This is a notification from the client that it's ready.
                # We don't need to send a response for notifications.
                logger.info("Received 'initialized' notification from client.")
                # Return a simple 204 No Content response without a body.
                # Using JSONResponse here would incorrectly add a 'null' body.
                return Response(status_code=204)
            else:
                # For other notifications, we can just log them and ignore.
                logger.warning(f"Received an unsupported notification: {method}")
                return Response(status_code=204)

        if method == "initialize":
            response_payload = {
                "protocolVersion": "2025-06-18",
                "serverInfo": {
                    "name": "Calculator MCP Server",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {
                        "listChanged": False
                    },
                    "prompts": {},
                    "resources": {},
                    "logging": {},
                    "roots": {}
                }
            }
            return create_and_log_response(json_rpc_response(request_id, response_payload))

        if not all([request_id, method]):
            return create_and_log_response(
                json_rpc_error(None, -32600, "Invalid Request"),
                status_code=400,
            )

        if method == "tools/list":
            all_funcs = registry.list_functions()
            tools_list = []
            for name, meta in all_funcs.items():
                tools_list.append({
                    "name": name,
                    "description": meta.get("description", ""),
                    "inputSchema": {
                        "type": "object",
                        "properties": meta.get("parameters", {}),
                    }
                })
            return create_and_log_response(json_rpc_response(request_id, {"tools": tools_list}))

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            func_meta = registry.get_function(tool_name)
            if not func_meta:
                return create_and_log_response(json_rpc_error(request_id, -32601, "Method not found"), status_code=404)

            handler = func_meta["handler"]
            try:
                result = handler(**arguments)
                return create_and_log_response(json_rpc_response(request_id, {"content": [{"type": "text", "text": str(result)}]}))
            except CalcError as e:
                return create_and_log_response(json_rpc_error(request_id, -32000, f"Calculation Error: {e}"), status_code=400)
            except Exception as e:
                return create_and_log_response(json_rpc_error(request_id, -32000, f"Server Error: {e}"), status_code=500)

        else:
            return create_and_log_response(json_rpc_error(request_id, -32601, "Method not found"), status_code=404)

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        response = json_rpc_error(None, -32700, f"Parse error: {str(e)}")
        logger.info(f"MCP-RESPONSE-BODY: {response}")
        return JSONResponse(
            status_code=500,
            content=response,
        )


@app.get("/")
async def mcp_sse_handler(request: Request):
    """Handles the client's GET request to establish a server-sent events (SSE) stream."""
    async def event_stream():
        try:
            while True:
                # Yield a keep-alive message to prevent the connection from timing out
                # and to make this a valid async generator.
                yield "data: \n\n"
                await asyncio.sleep(15)
                if await request.is_disconnected():
                    logger.info("Client disconnected from SSE stream.")
                    break
        except asyncio.CancelledError:
            logger.info("SSE stream cancelled by client.")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
