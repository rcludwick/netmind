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
    port = 8000
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
    """Starts a dummy TCP echo server in a separate thread."""
    port = 9999
    stop_event = threading.Event()

    def run_server():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', port))
        sock.listen(1)
        sock.settimeout(1.0) # Check stop_event periodically
        
        while not stop_event.is_set():
            try:
                conn, _ = sock.accept()
                with conn:
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break
                        conn.sendall(data)
            except socket.timeout:
                continue
            except Exception:
                break
        sock.close()

    thread = threading.Thread(target=run_server)
    thread.daemon = True
    thread.start()
    
    # Wait a bit for server to start
    time.sleep(1)
    
    yield port
    
    stop_event.set()
    thread.join(timeout=2)

@pytest.fixture
async def manual_page():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        yield page
        await browser.close()
