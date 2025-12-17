import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastmcp import FastMCP
from mcp.server.fastmcp import Context

from .core import engine, state_manager

# --- Configuration ---
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("NetMind Initializing...")
    yield
    # Shutdown logic
    print("NetMind Shutting down...")

# --- MCP Server Definition ---
mcp = FastMCP("NetMind Network Intelligence")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)