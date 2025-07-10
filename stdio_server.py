from __future__ import annotations

"""A lightweight, stdio-based MCP server for local tool integration."""

import json
import logging
import sys
from typing import Any, Dict

# Assuming the script is run from the project root, we can import from the server module.
from server.registry import registry, CalcError

# Configure logging to write to stderr to avoid interfering with the stdio communication channel.
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s - stdio-server - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_json_rpc_response(request_id: int | str, result: Any) -> Dict[str, Any]:
    """Constructs a successful JSON-RPC response dictionary."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def create_json_rpc_error(
    request_id: int | str | None,
    code: int,
    message: str,
) -> Dict[str, Any]:
    """Constructs a JSON-RPC error response dictionary."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def send_response(response: Dict[str, Any]):
    """Serializes a response dictionary to JSON and sends it to stdout with framing."""
    message_body = json.dumps(response)
    # Use Content-Length framing to delineate messages, as required by some clients.
    header = f"Content-Length: {len(message_body.encode('utf-8'))}\r\n\r\n"
    sys.stdout.write(header)
    sys.stdout.write(message_body)
    sys.stdout.flush()
    logger.info(f"Sent response: {message_body}")


def handle_request(body: Dict[str, Any]):
    """Processes a single JSON-RPC request and sends a response."""
    request_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    # Handle notifications (requests without an ID)
    if request_id is None:
        if method == "notifications/initialized":
            logger.info("Client initialized successfully.")
        else:
            logger.warning(f"Received unsupported notification: {method}")
        return  # Do not send a response for notifications

    if method == "initialize":
        response_payload = {
            "protocolVersion": "2025-06-18",
            "serverInfo": {"name": "Calculator Stdio MCP Server", "version": "1.0.0"},
            "capabilities": {"tools": {"listChanged": False}},
        }
        send_response(create_json_rpc_response(request_id, response_payload))

    elif method == "tools/list":
        all_funcs = registry.list_functions()
        tools_list = [
            {
                "name": name,
                "description": meta.get("description", ""),
                "inputSchema": {
                    "type": "object",
                    "properties": meta.get("parameters", {}),
                },
            }
            for name, meta in all_funcs.items()
        ]
        send_response(create_json_rpc_response(request_id, {"tools": tools_list}))

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        func_meta = registry.get_function(tool_name)

        if not func_meta:
            send_response(create_json_rpc_error(request_id, -32601, "Method not found"))
            return

        try:
            result = func_meta["handler"](**arguments)
            # The result for a tool call must be wrapped correctly.
            response_content = {"content": [{"type": "text", "text": str(result)}]}
            send_response(create_json_rpc_response(request_id, response_content))
        except CalcError as e:
            send_response(create_json_rpc_error(request_id, -32000, f"Calculation Error: {e}"))
        except Exception as e:
            logger.error(f"Error during tool call: {e}", exc_info=True)
            send_response(create_json_rpc_error(request_id, -32000, f"Server Error: {e}"))

    else:
        send_response(create_json_rpc_error(request_id, -32601, "Method not found"))


def main():
    """Main loop to read from stdin, process requests, and write to stdout."""
    logger.info("stdio_server.py is running and waiting for requests...")
    while True:
        line = sys.stdin.readline()
        if not line:
            logger.info("Input stream closed. Shutting down.")
            break

        # Process headers to find Content-Length
        if line.strip().lower().startswith("content-length:"):
            try:
                content_length = int(line.split(":")[1].strip())
                # Read the blank line after headers
                sys.stdin.readline()
                # Read the message body
                message_body = sys.stdin.read(content_length)
                logger.info(f"Received request: {message_body}")
                request_data = json.loads(message_body)
                handle_request(request_data)
            except (ValueError, json.JSONDecodeError, IndexError) as e:
                logger.error(f"Failed to parse request: {e}", exc_info=True)
                send_response(create_json_rpc_error(None, -32700, "Parse error"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server shut down by user.")
    except Exception as e:
        logger.critical(f"An unhandled exception occurred: {e}", exc_info=True)
