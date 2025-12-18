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
    local_port: int
    target_host: str
    target_port: int
    name: str
    protocol: str = "raw"

class TestConnectionRequest(BaseModel):
    target_host: str
    target_port: int

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("NetMind Initializing...")
    await engine.start_monitor()
    yield
    # Shutdown logic
    print("NetMind Shutting down...")
    await engine.shutdown()

# --- MCP Server Definition ---
mcp = FastMCP("NetMind Network Intelligence")

@mcp.tool()
def get_help() -> str:
    """
    Returns a comprehensive guide on how to use NetMind to debug network traffic.
    Read this if you are unsure how to proceed.
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
    """
    Start a new TCP proxy.
    
    Args:
        local_port: The port on localhost to listen on.
        target_host: The destination hostname or IP.
        target_port: The destination port.
        name: A human-readable name for this connection.
        protocol: 'raw' for generic TCP, 'hamlib' for Radio control.
    """
    try:
        msg = await engine.add_proxy(local_port, target_host, target_port, name, protocol)
        return msg
    except Exception as e:
        return f"Failed to start proxy: {str(e)}"

@mcp.tool()
async def list_traffic_history(limit: int = 10) -> str:
    """Get the most recent packets seen by the system."""
    history = list(state_manager.packet_log)[-limit:]
    return json.dumps([h.__dict__ for h in history], indent=2)

@mcp.resource("tcp://proxies/active")
def list_active_proxies() -> str:
    """Returns a list of currently active TCP proxies."""
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
    return templates.TemplateResponse(request, "dashboard.html", {
        "proxies": state_manager.active_proxies.values()
    })

@app.post("/api/proxies")
async def create_proxy(proxy: ProxyRequest):
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
    """Get the most recent packets seen by the system, optionally filtered by proxy name."""
    history = list(state_manager.packet_log)
    if proxy_name:
        history = [h for h in history if h.proxy_name == proxy_name]
    return [h.__dict__ for h in history[-limit:]]

@app.delete("/api/proxies/{port}")
async def remove_proxy(port: int):
    try:
        msg = await engine.remove_proxy(port)
        return {"status": "success", "message": msg}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/proxies/test")
async def test_connection(req: TestConnectionRequest):
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

@app.websocket("/ws/monitor")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    queue = await state_manager.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        state_manager.unsubscribe(queue)

def main():
    import uvicorn
    uvicorn.run("netmind.app:app", host="0.0.0.0", port=8002, reload=True)

if __name__ == "__main__":
    main()
