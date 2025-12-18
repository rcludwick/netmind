import pytest
import threading
import time
import socket
import uvicorn
import asyncio
from netmind.app import app

@pytest.fixture(scope="session")
def server_url():
    """Starts the FastAPI server in a separate thread."""
    port = 8002
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    
    thread = threading.Thread(target=server.run)
    thread.daemon = True
    thread.start()
    
    # Wait for server to boot
    time.sleep(2)
    return f"http://127.0.0.1:{port}"

@pytest.fixture(scope="session")
def echo_server():
    """Starts a threaded TCP echo server."""
    import socketserver
    
    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True
        daemon_threads = True

    class EchoHandler(socketserver.BaseRequestHandler):
        def handle(self):
            try:
                while True:
                    data = self.request.recv(1024)
                    if not data:
                        break
                    self.request.sendall(data)
            except Exception:
                pass

    port = 9999
    server = ThreadedTCPServer(('127.0.0.1', port), EchoHandler)
    
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    
    # Wait a bit for server to start
    time.sleep(1)
    
    yield port
    
    server.shutdown()
    server.server_close()

@pytest.fixture
async def manual_page():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        yield page
        await browser.close()

@pytest.fixture(autouse=True)
async def cleanup_engine():
    from netmind.core import engine, state_manager
    # Run before test
    yield
    # Run after test
    await engine.stop_all_proxies()
    state_manager.packet_log.clear()
    state_manager.subscribers.clear()
    # Restart engine for next test if needed (shutdown clears proxies)

