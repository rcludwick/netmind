# Project Description
This is the **NetMind** project. It is a dual-interface TCP debugging tool and MCP server designed for AI agents and human operators. It intercepts, decodes (e.g. Hamlib), and logs TCP traffic.

## Architecture
- **Backend**: Python (FastAPI, Uvicorn, MCP, FastMCP).
- **Frontend**: HTML/JS Dashboard (Jinja2 served by FastAPI).
- **Core Logic**: `core.py` handles the proxy engine and state management.

## Codebase Structure
- `netmind/`: Main package.
    - `app.py`: FastAPI server & MCP SSE endpoint.
    - `core.py`: TCP Proxy engine, state management, and semantic parsing logic.
    - `mcp_stdio.py`: Stdio entry point for MCP.
    - `protocols.py`: Protocol definitions and parsers (e.g. Hamlib).
    - `templates/`: Jinja2 templates for the dashboard.
- `tests/`: Pytest suite (Playwright E2E and unit tests).
- `Makefile`: `install`, `run`, `test` targets.

## Rules

### 1. Testing Requirements
All changes must be verified with the appropriate test suite.
- **Backend/Integration**: MUST have a **Pytest** test.
    - Run: `make test`
    - Location: `tests/`
- **MCP Tools**: Ensure MCP tools (`start_proxy` etc.) are verified.

### 2. Style Guidelines
- **Python**: Follow PEP 8.
- **Python**: Use **Google Style Docstrings** for all functions and classes.
- **Frontend**: Clean, readable HTML/JS.

### 3. Build System
- Use the `Makefile` for all build and test operations.
    - `make install`: Install dependencies.
    - `make run`: Run the server.
    - `make test`: Run all tests.

## Important Context for AI Agents
- **MCP**: NetMind is an MCP server. It exposes tools (`start_proxy`, `list_traffic_history`) and resources (`tcp://proxies/active`).
- **Hamlib**: The `hamlib` protocol parser is critical for debugging the parent project (MultiRig).
- **State**: `state_manager` in `core.py` is the singleton source of truth for active proxies and packet logs.
