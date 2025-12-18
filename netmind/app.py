"""
NetMind Application Server.

This module defines the FastAPI application for NetMind, including API endpoints,
MCP server integration, and WebSocket handlers for real-time monitoring.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastmcp import FastMCP
from mcp.server.fastmcp import Context
from pydantic import BaseModel

from .core import engine, state_manager

# --- Configuration ---
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

class ProxyRequest(BaseModel):
    """Request model for creating a new TCP proxy.

    Attributes:
        local_port: The local port to listen on.
        target_host: The target hostname or IP address.
        target_port: The target port to forward traffic to.
        name: A human-readable name for the proxy connection.
        protocol: The protocol to use for parsing (default: "raw").
    """
    local_port: int
    target_host: str
    target_port: int
    name: str
    protocol: str = "raw"

class TestConnectionRequest(BaseModel):
    """Request model for testing a connection to a target.

    Attributes:
        target_host: The target hostname or IP address.
        target_port: The target port to connect to.
    """
    target_host: str
    target_port: int

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup and shutdown).

    Args:
        app: The FastAPI application instance.
    """
    # Startup logic
    print("NetMind Initializing...")
    
    # Initialize proxies from environment variable
    if "NETMIND_PROXIES" in os.environ:
        try:
            proxies = json.loads(os.environ["NETMIND_PROXIES"])
            for p in proxies:
                try:
                    await engine.add_proxy(
                        int(p["local_port"]), 
                        p["target_host"], 
                        int(p["target_port"]), 
                        p["name"], 
                        p.get("protocol", "raw")
                    )
                    print(f"Started proxy: {p['name']}")
                except Exception as e:
                    print(f"Failed to start proxy {p.get('name')}: {e}")
        except Exception as e:
            print(f"Error loading proxies from env: {e}")

    await engine.start_monitor()
    yield
    # Shutdown logic
    print("NetMind Shutting down...")
    await engine.shutdown()

# --- MCP Server Definition ---
mcp = FastMCP("NetMind Network Intelligence")

@mcp.tool()
def get_help() -> str:
    """Returns a comprehensive guide on how to use NetMind to debug network traffic.

    Read this if you are unsure how to proceed.

    Returns:
        A formatted markdown string containing the user guide.
    """
    return """
# NetMind User Guide for AI Agents

You are currently connected to **NetMind**, a network interception and analysis tool. Your goal is often to "Man-in-the-Middle" (MITM) a TCP connection to debug what is actually being sent on the wire.

## 🚀 Recommended Workflow

1.  **Check Existing Proxies**:
    First, see if a proxy is already running for the target you are interested in.
    *   Use the resource `tcp://proxies/active` or the tool `list_active_proxies` (if available) to see what ports are occupied.

2.  **Start a Proxy**:
    If no proxy exists, you need to route traffic through NetMind.
    *   Use the `start_proxy` tool.
    *   **Crucial**: If debugging a Radio/Hamlib connection, set `protocol='hamlib'`. This enables the semantic parser which translates opaque bytes like `\\x46\\x20\\x31...` into readable text like `SET FREQ: 14000000`.
    *   *Example*: `start_proxy(local_port=9000, target_host='localhost', target_port=4532, name='RigDebug', protocol='hamlib')`
    *   Now, instruct the user (or the client software) to connect to **localhost:9000** instead of the original target port.

3.  **Analyze Traffic**:
    Once traffic is flowing, inspect the logs to find errors or confirm behavior.
    *   Use `list_traffic_history(limit=20)` to see the recent Request/Response cycle.
    *   Look at the `semantic` field.
        *   `RAW`: formatting indicates the parser couldn't understand the packet (or protocol='raw').
        *   `SET FREQ`, `GET MODE`: indicates successful parsing.
        *   `RPRT -1`: In Hamlib, this specifically means the Rig **rejected** the command (Command Error).
        *   `RPRT -5`: I/O Error.

## 🧠 Debugging Scenarios

*   **"The rig isn't responding"**:
    Start a proxy. Check `list_traffic_history`.
    *   If you see `TX` (commands sent) but no `RX` (responses), the physical link to the rig might be broken, or the baud rate is wrong.
    *   If you see `RX` garbage, the baud rate might be mismatched.

*   **"Command rejected"**:
    If you see `RPRT -1` in the `semantic` or `data_str` fields:
    *   Compare the `TX` command immediately preceding it.
    *   Does the frequency support the current mode?
    *   Are the arguments within valid ranges?
    """

@mcp.tool()
async def start_proxy(local_port: int, target_host: str, target_port: int, name: str, protocol: str = "raw"):
    """Start a new TCP proxy.
    
    Args:
        local_port: The port on localhost to listen on.
        target_host: The destination hostname or IP.
        target_port: The destination port.
        name: A human-readable name for this connection.
        protocol: 'raw' for generic TCP, 'hamlib' for Radio control.

    Returns:
        A success message if the proxy started, or an error message string.
    """
    try:
        msg = await engine.add_proxy(local_port, target_host, target_port, name, protocol)
        return msg
    except Exception as e:
        return f"Failed to start proxy: {str(e)}"

@mcp.tool()
async def list_traffic_history(limit: int = 10) -> str:
    """Get the most recent packets seen by the system.

    Args:
        limit: The maximum number of packets to return.

    Returns:
        A JSON-formatted string containing the packet history.
    """
    history = list(state_manager.packet_log)[-limit:]
    return json.dumps([h.__dict__ for h in history], indent=2)

@mcp.resource("tcp://proxies/active")
def list_active_proxies() -> str:
    """Returns a list of currently active TCP proxies.

    Returns:
        A JSON-formatted string listing active proxies.
    """
    proxies = [
        {"name": p.name, "listen": p.local_port, "target": f"{p.target_host}:{p.target_port}", "proto": p.protocol}
        for p in state_manager.active_proxies.values()
    ]
    return json.dumps(proxies, indent=2)

# --- FastAPI App ---
app = FastAPI(lifespan=lifespan)

# Mount MCP
mcp_app = mcp.http_app(transport="sse")
app.mount("/mcp", mcp_app)

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Render the NetMind dashboard.

    Args:
        request: The incoming HTTP request.

    Returns:
        The rendered HTML dashboard template.
    """
    return templates.TemplateResponse(request, "dashboard.html", {
        "proxies": state_manager.active_proxies.values()
    })

@app.post("/api/proxies")
async def create_proxy(proxy: ProxyRequest):
    """API endpoint to create a new proxy.

    Args:
        proxy: The proxy configuration.

    Returns:
        A JSON response indicating success.

    Raises:
        HTTPException: If the proxy fails to start.
    """
    try:
        msg = await engine.add_proxy(
            proxy.local_port, 
            proxy.target_host, 
            proxy.target_port, 
            proxy.name, 
            proxy.protocol
        )
        return {"status": "success", "message": msg}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/history")
async def get_history(limit: int = 10, proxy_name: Optional[str] = None):
    """Get the most recent packets seen by the system, optionally filtered by proxy name.

    Args:
        limit: Maximum number of packets to return.
        proxy_name: Optional name of the proxy to filter by.

    Returns:
        A list of packet dictionaries.
    """
    history = list(state_manager.packet_log)
    if proxy_name:
        history = [h for h in history if h.proxy_name == proxy_name]
    return [h.__dict__ for h in history[-limit:]]

@app.delete("/api/proxies/{port}")
async def remove_proxy(port: int):
    """Remove a proxy by its local port.

    Args:
        port: The local port of the proxy to remove.

    Returns:
        A JSON response indicating success.

    Raises:
        HTTPException: If the proxy is not found or cannot be removed.
    """
    try:
        msg = await engine.remove_proxy(port)
        return {"status": "success", "message": msg}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/proxies/test")
async def test_connection(req: TestConnectionRequest):
    """Test a connection to a target host and port.

    Args:
        req: The connection details to test.

    Returns:
        A JSON response indicating success or failure.
    """
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(req.target_host, req.target_port),
            timeout=3.0
        )
        writer.close()
        await writer.wait_closed()
        return {"status": "success", "message": "Connection successful"}
    except Exception as e:
        # We return 200 even on failure so frontend can display message easily, 
        # but with status=error
        return {"status": "error", "message": f"Connection failed: {str(e)}"}

@app.post("/api/shutdown")
async def shutdown_server():
    """Shuts down the NetMind server.

    Returns:
        A JSON response indicating that shutdown has been initiated.
    """
    # Schedule process exit
    loop = asyncio.get_running_loop()
    loop.call_later(0.1, os._exit, 0)
    return {"status": "success", "message": "Server shutting down..."}

@app.websocket("/ws/monitor")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring.

    Args:
        websocket: The WebSocket connection.
    """
    await websocket.accept()
    queue = await state_manager.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        state_manager.unsubscribe(queue)

def main():
    """Main entry point for running the NetMind server."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="NetMind Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8002, help="Port to bind to (default: 8002)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--proxy", action="append", help="Start a proxy (format: name:local_port:target_host:target_port)")

    args = parser.parse_args()

    if args.proxy:
        proxies = []
        for proxy_str in args.proxy:
            try:
                # Expected format: name:local_port:target_host:target_port
                parts = proxy_str.split(":")
                if len(parts) >= 4:
                    proxies.append({
                        "name": parts[0],
                        "local_port": parts[1],
                        "target_host": parts[2],
                        "target_port": parts[3]
                    })
                else:
                    print(f"Invalid proxy format (ignored): {proxy_str}")
            except Exception as e:
                print(f"Error parsing proxy '{proxy_str}': {e}")
        
        if proxies:
            os.environ["NETMIND_PROXIES"] = json.dumps(proxies)

    uvicorn.run("netmind.app:app", host=args.host, port=args.port, reload=args.reload)

if __name__ == "__main__":
    main()
