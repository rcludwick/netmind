import pytest
import os
import json
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI
from netmind.app import lifespan

@pytest.mark.asyncio
async def test_lifespan_starts_proxies():
    # Setup env
    proxies = [
        {"name": "EnvProxy", "local_port": "9999", "target_host": "example.com", "target_port": "80"}
    ]
    os.environ["NETMIND_PROXIES"] = json.dumps(proxies)
    
    # Mock engine methods
    # engine is imported in app.py from core.py
    # We patch netmind.app.engine
    
    with patch("netmind.app.engine") as mock_engine:
        mock_engine.add_proxy = AsyncMock()
        mock_engine.start_monitor = AsyncMock()
        mock_engine.shutdown = AsyncMock()

        async with lifespan(FastAPI()):
            # Verify add_proxy was called
            # Note: arguments are (local_port, target_host, target_port, name, protocol)
            mock_engine.add_proxy.assert_awaited_with(
                9999, "example.com", 80, "EnvProxy", "raw"
            )
            
            mock_engine.start_monitor.assert_awaited_once()
        
        mock_engine.shutdown.assert_awaited_once()
    
    # Cleanup
    if "NETMIND_PROXIES" in os.environ:
        del os.environ["NETMIND_PROXIES"]
