import pytest
import asyncio
from playwright.async_api import Page, expect
from netmind.app import app
from netmind.core import engine

# --- Tests ---

@pytest.mark.asyncio
async def test_simple():
    await asyncio.sleep(0.01)

@pytest.mark.asyncio
async def test_page_loads(manual_page: Page, server_url):
    """Verifies the dashboard loads."""
    page = manual_page
    await page.goto(server_url)
    await expect(page).to_have_title("NetMind | TCP Debugger")
    await expect(page.get_by_role("heading", name="Active Proxies")).to_be_visible()

@pytest.mark.asyncio
async def test_proxy_flow_and_ui_update(manual_page: Page, server_url, echo_server):
    """
    Full End-to-End Test:
    1. Start a Proxy via the Engine (simulating MCP).
    2. Connect to the Proxy via Python client.
    3. Send data.
    4. Verify data appears in the Web UI (Playwright).
    """
    page = manual_page
    # 1. Start Proxy
    proxy_port = 9090
    await engine.add_proxy(
        local_port=proxy_port, 
        target_host="127.0.0.1", 
        target_port=echo_server, 
        name="Test-Proxy",
        protocol="raw"
    )

    # 2. Open Page
    await page.goto(server_url)
    # Check if proxy appears in sidebar
    await expect(page.get_by_text("Test-Proxy")).to_be_visible()

    # 3. Send Traffic
    msg = b"HELLO_MCP_WORLD"
    reader, writer = await asyncio.open_connection("127.0.0.1", proxy_port)
    writer.write(msg)
    await writer.drain()
    
    # Read echo to ensure round-trip
    response = await reader.read(100)
    assert response == msg
    writer.close()
    await writer.wait_closed()

    # 4. Verify in UI
    # The websocket should update the table
    # We look for the row containing our message
    await expect(page.locator("td", has_text="HELLO_MCP_WORLD").first).to_be_visible()
    # Check TX and RX arrows exist (since echo happened)
    await expect(page.locator(".tx")).to_be_visible()
    await expect(page.locator(".rx")).to_be_visible()

@pytest.mark.asyncio
async def test_hamlib_translation(manual_page: Page, server_url, echo_server):
    """
    Verifies that Hamlib commands are translated in the UI.
    """
    page = manual_page
    proxy_port = 9091
    await engine.add_proxy(
        local_port=proxy_port, 
        target_host="127.0.0.1", 
        target_port=echo_server, 
        name="Radio-One",
        protocol="hamlib"
    )

    await page.goto(server_url)

    # Send Hamlib "Set Frequency" command
    # F 14074000
    cmd = b"F 14074000"
    reader, writer = await asyncio.open_connection("127.0.0.1", proxy_port)
    writer.write(cmd)
    await writer.drain()
    writer.close()
    await writer.wait_closed()

    # Verify the SEMANTIC translation appears
    await expect(page.locator(".semantic", has_text="SET FREQ: 14074000")).to_be_visible()