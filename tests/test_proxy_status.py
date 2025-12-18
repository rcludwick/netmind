import pytest
import asyncio
from netmind.core import engine, state_manager, StatusEvent

@pytest.mark.asyncio
async def test_health_check_logic(echo_server):
    # 1. Start a proxy pointing to a valid echo server
    proxy_port = 9100
    await engine.add_proxy(
        local_port=proxy_port,
        target_host="127.0.0.1",
        target_port=echo_server,
        name="HealthyProxy"
    )
    
    # 2. Start a proxy pointing to a bad port
    bad_proxy_port = 9101
    await engine.add_proxy(
        local_port=bad_proxy_port,
        target_host="127.0.0.1",
        target_port=1, # Unlikely to be open
        name="UnhealthyProxy"
    )
    
    # Subscribe to events
    queue = await state_manager.subscribe()
    
    # Run one iteration of the health check
    # We call the internal method directly to avoid waiting for the loop sleep
    for proxy in engine.proxies:
        await engine._check_proxy_health(proxy)
        
    # Check for events
    events = []
    while not queue.empty():
        events.append(await queue.get())
        
    status_events = [e for e in events if e.get('type') == 'status']
    
    # Verify Healthy Proxy
    healthy_evt = next((e for e in status_events if e['local_port'] == proxy_port), None)
    assert healthy_evt is not None
    assert healthy_evt['status'] == 'online'
    assert healthy_evt['error_msg'] is None
    
    # Verify Unhealthy Proxy
    unhealthy_evt = next((e for e in status_events if e['local_port'] == bad_proxy_port), None)
    assert unhealthy_evt is not None
    assert unhealthy_evt['status'] == 'offline'
    assert unhealthy_evt['error_msg'] is not None
    
    # Clean up
    await engine.remove_proxy(proxy_port)
    await engine.remove_proxy(bad_proxy_port)
