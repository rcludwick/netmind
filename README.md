# NetMind

**NetMind** is a dual-interface TCP debugging tool designed for AI agents and human operators. It serves as both a **Model Context Protocol (MCP)** server and a real-time **Web Dashboard**.

It is specifically optimized for debugging Hamlib (Rig Control) applications by translating raw TCP packets into semantic descriptions (e.g., `F 14074000` → `SET FREQ: 14074000`), but it works as a robust generic TCP proxy for any protocol.

## ✨ Features

- **TCP Proxy Engine**: Spawns multiple listeners that forward traffic to target hosts.
- **MCP Server**: Allows AI agents (like Claude Desktop, Cursor, etc.) to programmatically start proxies and inspect traffic history.
- **Web Dashboard**: Real-time WebSocket-based view of packets (TX/RX) with hex dumps and semantic translation.
- **Hamlib Support**: Built-in parser for radio control protocols.
- **Repo-Ready**: Built with `uv` for modern Python dependency management.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/netmind.git
    cd netmind
    ```

2.  **Install dependencies:**
    ```bash
    uv sync --all-extras
    ```

3.  **Install Playwright browsers (for testing):**
    ```bash
    uv run playwright install chromium
    ```

### Running the Server

Start the application (Web UI + MCP Adapter):

```bash
uv run netmind-server
```

- **Web Dashboard**: [http://localhost:8002](http://localhost:8002)
- **MCP SSE Endpoint**: `http://localhost:8002/mcp/sse`

## 💻 CLI Usage

You can start the server with pre-configured proxies using the command line.

### Start Multiple Proxies

Use the `--proxy` flag to define one or more proxies at startup.
Format: `name:local_port:target_host:target_port`

```bash
uv run netmind-server \
  --proxy "RigControl:9000:192.168.1.50:4532" \
  --proxy "WebServer:8080:localhost:80"
```

**Options:**

- `--host`: Host to bind to (default: `0.0.0.0`)
- `--port`: Port to bind to (default: `8002`)
- `--reload`: Enable auto-reload for development
- `--proxy`: Start a proxy (can be used multiple times)

## 🤖 MCP Integration for AI Agents

NetMind is designed to be a "tool" for other AI agents. It exposes a Model Context Protocol (MCP) server that provides programmatic access to network interception and analysis.

### Connection Configuration

AI Clients (like Claude Desktop, Cursor, or custom agents) can connect to NetMind using one of two transports:

**1. Stdio (Recommended for Local Clients)**
Use this command to run NetMind as a subprocess:
```bash
uv run -m netmind.mcp_stdio
```

**2. SSE (Server-Sent Events)**
If running the web server (`netmind-server`), the MCP endpoint is available at:
- Endpoint: `http://localhost:8002/mcp/sse`

### 🛠️ Tools

These tools allow the AI to manipulate the network proxy engine.

- **`start_proxy`**: Starts a new TCP listener that intercepts and forwards traffic.
    - `local_port`: Port NetMind listens on.
    - `target_host`: Destination hostname.
    - `target_port`: Destination port.
    - `name`: Human-readable label.
    - `protocol`: `"raw"` (default) or `"hamlib"`.
- **`list_traffic_history`**: Retrieves recent network packets (TX/RX).
- **`tcp://proxies/active`** (Resource): JSON list of active proxies.

## 🧪 Testing

NetMind uses Playwright for End-to-End (E2E) Network Validation.

```bash
uv run pytest
```

### How to Write a Debug Test

If you are debugging a specific Hamlib behavior, you can write a test case to mechanically reproduce network issues.

```python
import pytest
from playwright.async_api import Page, expect
from netmind.core import engine
import asyncio

@pytest.mark.asyncio
async def test_radio_frequency_update(page: Page, server_url):
    # 1. Setup: Start a proxy
    await engine.add_proxy(9000, "127.0.0.1", 4532, "MyRadio", "hamlib")
    
    # 2. Open the Inspector
    await page.goto(server_url)

    # 3. Action: Send raw bytes to the proxy
    reader, writer = await asyncio.open_connection("127.0.0.1", 9000)
    writer.write(b"F 14200000") # Hamlib 'Set Frequency'
    await writer.drain()
    writer.close()

    # 4. Assertion: Verify the UI decoded it correctly
    await expect(page.locator(".semantic")).to_contain_text("SET FREQ: 14200000")
```

## 📻 Supported Hamlib Commands

The parser currently supports:
- **F**: Set Frequency
- **f**: Get Frequency
- **M**: Set Mode
- **m**: Get Mode
- **T**: PTT (Push to Talk)
