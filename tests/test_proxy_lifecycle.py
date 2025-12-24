import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from netmind.app import app
from netmind.core import engine

@pytest.mark.asyncio
async def test_proxy_lifecycle(echo_server):
    """
    Verifies the full lifecycle of a proxy: creation, verification, and removal.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        
        # 1. Test Connection Endpoint
        # Should succeed (echo server is running)
        resp = await ac.post("/api/proxies/test", json={
            "target_host": "127.0.0.1",
            "target_port": echo_server
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

        # Should fail (invalid port)
        resp = await ac.post("/api/proxies/test", json={
            "target_host": "127.0.0.1",
            "target_port": 1
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"

        # 2. Create Proxy
        proxy_port = 9095
        resp = await ac.post("/api/proxies", json={
            "local_port": proxy_port,
            "target_host": "127.0.0.1",
            "target_port": echo_server,
            "name": "Lifecycle-Test",
            "protocol": "raw"
        })
        assert resp.status_code == 200
        
        # Verify it's active in engine
        # Note: Depending on parallel tests, there might be other proxies, so we check for existence
        found = any(p.config.local_port == proxy_port for p in engine.proxies)
        assert found

        # 3. Remove Proxy
        resp = await ac.delete(f"/api/proxies/{proxy_port}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

        # Verify it's gone
        found = any(p.config.local_port == proxy_port for p in engine.proxies)
        assert not found

        # 4. Remove Non-existent Proxy
        resp = await ac.delete(f"/api/proxies/{proxy_port}")
        assert resp.status_code == 404
