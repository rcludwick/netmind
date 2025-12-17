NetMindNetMind is a dual-interface TCP debugging tool designed for AI agents and human operators. It serves as both a Model Context Protocol (MCP) server and a real-time web dashboard.It is specifically optimized for debugging Hamlib (Rig Control) applications by translating raw TCP packets into semantic descriptions (e.g., F 14074000 → SET FREQ: 14074000), but it works as a generic TCP proxy for any protocol.FeaturesTCP Proxy Engine: Spawns multiple listeners that forward traffic to target hosts.MCP Server: allows AI agents (like Claude Desktop, Cursor, etc.) to programmatically start proxies and inspect traffic history.Web Dashboard: Real-time WebSocket-based view of packets (TX/RX) with hex dumps and semantic translation.Hamlib Support: Built-in parser for radio control protocols.Repo-Ready: Built with uv for modern Python dependency management.🚀 Quick StartPrerequisitesPython 3.11+uv (recommended)Installation# 1. Clone the repository
git clone [https://github.com/yourusername/netmind.git](https://github.com/yourusername/netmind.git)
cd netmind

# 2. Install dependencies
uv sync --all-extras

# 3. Install Playwright browsers (for testing)
uv run playwright install chromium
Running the ServerStart the application (Web UI + MCP Adapter):uv run uvicorn netmind.app:app --host 0.0.0.0 --port 8000 --reload
Web Dashboard: http://localhost:8000MCP SSE Endpoint: http://localhost:8000/mcp/sse## 🤖 MCP Integration for AI Agents

NetMind is designed to be a "tool" for other AI agents. It exposes a Model Context Protocol (MCP) server that provides programmatic access to network interception and analysis.

### Connection Configuration

AI Clients (like Claude Desktop, Cursor, or custom agents) can connect to NetMind using one of two transports:

**1. Stdio (Recommended for Local Clients)**
Use this command to run NetMind as a subprocess:
```bash
uv run -m netmind.mcp_stdio
```

**2. SSE (Server-Sent Events)**
If running the web server (`uv run uvicorn netmind.app:app ...`), the MCP endpoint is available at:
- Endpoint: `http://localhost:8000/sse`

### 🛠️ Tools

These tools allow the AI to manipulate the network proxy engine.

#### `start_proxy`
Starts a new TCP listener that intercepts and forwards traffic.

*   **Description**: Create a new proxy instance.
*   **Arguments**:
    *   `local_port` (int): The port NetMind will listen on (e.g., `9000`).
    *   `target_host` (string): The destination hostname (e.g., `localhost` or `192.168.1.50`).
    *   `target_port` (int): The destination port (e.g., `4532`).
    *   `name` (string): A human-readable label for this connection (e.g., `"Kenwood TS-590"`).
    *   `protocol` (string): Parsing mode. Options:
        *   `"raw"`: No parsing (default).
        *   `"hamlib"`: Decodes amateur radio control commands (Rig Control).

#### `list_traffic_history`
Retrieves the most recent network packets captured by the proxies.

*   **Description**: Get a log of TX/RX events to analyze communication.
*   **Arguments**:
    *   `limit` (int, default=10): Number of recent packets to retrieve.

### 📦 Resources

Resources provide read-only context about the system state.

*   `tcp://proxies/active`
    *   **Description**: Returns a JSON list of all currently running proxy listeners and their configurations. Use this to check what ports are already occupied.

### 🧠 System Prompt Context

If you are an AI assistant using this tool, you can adopt the following persona:

> "I have access to NetMind, a network interception tool. I can spin up TCP proxies to 'man-in-the-middle' connections between clients and servers. This allows me to see the exact raw bytes and decoded messages flowing between them, which is essential for debugging protocol errors, verifying data formats, or reverse-engineering network behavior. When debugging Hamlib/Rigctl, I should always use the 'hamlib' protocol to get semantic decoding."🧪 Testing with PlaywrightNetMind uses Playwright not just for UI testing, but for End-to-End (E2E) Network Validation.Because the web dashboard relies on WebSockets to display real-time TCP traffic, standard HTTP tests aren't enough. Our tests spawn the actual server, create real TCP connections, send bytes, and verify that the data appears in the browser DOM.Running the Suiteuv run pytest
How to Write a Debug TestIf you are debugging a specific Hamlib behavior, you can write a test case in tests/test_custom.py. This allows you to mechanically reproduce network issues.import pytest
from playwright.async_api import Page, expect
from netmind.core import engine
import asyncio

@pytest.mark.asyncio
async def test_radio_frequency_update(page: Page, server_url):
    # 1. Setup: Start a proxy (assuming a dummy target is running on 4532)
    await engine.add_proxy(9000, "127.0.0.1", 4532, "MyRadio", "hamlib")
    
    # 2. Open the Inspector
    await page.goto(server_url)

    # 3. Action: Send raw bytes to the proxy
    reader, writer = await asyncio.open_connection("127.0.0.1", 9000)
    writer.write(b"F 14200000") # Hamlib 'Set Frequency'
    await writer.drain()
    writer.close()

    # 4. Assertion: Verify the UI decoded it correctly
    # We expect the dashboard to show the semantic meaning, not just raw text
    await expect(page.locator(".semantic")).to_contain_text("SET FREQ: 14200000")
📻 Supported Hamlib CommandsThe src/netmind/protocols.py file currently supports:F: Set Frequencyf: Get FrequencyM: Set Modem: Get ModeT: PTT (Push to Talk)