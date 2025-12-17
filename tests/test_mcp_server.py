
import pytest
from mcp.client.sse import sse_client
from mcp import ClientSession

@pytest.mark.asyncio
async def test_mcp_server_tools(server_url):
    """
    Verifies that the MCP server exposes the expected tools.
    """
    sse_url = f"{server_url}/mcp/sse"
    
    async with sse_client(sse_url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            # List tools
            result = await session.list_tools()
            tools = {tool.name for tool in result.tools}
            
            assert "start_proxy" in tools
            assert "list_traffic_history" in tools

@pytest.mark.asyncio
async def test_mcp_server_resources(server_url):
    """
    Verifies that the MCP server exposes the expected resources.
    """
    sse_url = f"{server_url}/mcp/sse"
    
    async with sse_client(sse_url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            # List resources
            result = await session.list_resources()
            resources = {str(res.uri) for res in result.resources}
            
            assert "tcp://proxies/active" in resources
