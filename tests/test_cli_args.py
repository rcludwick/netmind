import sys
import os
import json
from unittest.mock import patch, MagicMock
from netmind.app import main

def test_main_arg_parsing():
    # Mock uvicorn.run to prevent server start
    with patch("uvicorn.run") as mock_run:
        # Mock sys.argv
        test_args = [
            "netmind-server",
            "--port", "9000",
            "--proxy", "proxy1:8080:example.com:80",
            "--proxy", "proxy2:8081:localhost:3000"
        ]
        with patch.object(sys, "argv", test_args):
            # Clear env var if exists
            if "NETMIND_PROXIES" in os.environ:
                del os.environ["NETMIND_PROXIES"]
                
            main()
            
            # Check uvicorn arguments
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["port"] == 9000
            
            # Check environment variable
            assert "NETMIND_PROXIES" in os.environ
            proxies = json.loads(os.environ["NETMIND_PROXIES"])
            assert len(proxies) == 2
            assert proxies[0]["name"] == "proxy1"
            assert proxies[0]["local_port"] == "8080"
            assert proxies[0]["target_host"] == "example.com"
            assert proxies[0]["target_port"] == "80"

def test_main_no_proxy_args():
    with patch("uvicorn.run") as mock_run:
        test_args = ["netmind-server"]
        with patch.object(sys, "argv", test_args):
            if "NETMIND_PROXIES" in os.environ:
                del os.environ["NETMIND_PROXIES"]
                
            main()
            
            # Should not set env var if no proxies provided (or it might remain if we don't clear it, but we cleared it)
            # Actually, in my code: if proxies: os.environ[...] = ...
            # So if no proxies, it doesn't touch os.environ.
            # But we should ensure it's not set from previous test if we run in same process.
            # The context manager below handles env var clearing usually, but here we do it manually.
            
            assert "NETMIND_PROXIES" not in os.environ
            
            # Check defaults
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["port"] == 8002
            assert call_kwargs["host"] == "0.0.0.0"
