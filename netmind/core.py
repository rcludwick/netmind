import asyncio
import time
import logging
import uuid
from collections import deque, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable
from .protocols import HamlibParser

logger = logging.getLogger("netmind.core")

@dataclass
class PacketEvent:
    id: str
    proxy_name: str
    direction: str  # "TX" or "RX"
    data_hex: str
    data_str: str
    semantic: str
    timestamp: float
    connection_id: str
    type: str = "packet"

@dataclass
class StatusEvent:
    local_port: int
    status: str  # "online", "offline"
    error_msg: Optional[str]
    type: str = "status"

@dataclass
class ProxyConfig:
    local_port: int
    target_host: str
    target_port: int
    name: str
    protocol: str = "raw"  # raw, hamlib
    status: str = "unknown"
    error_msg: Optional[str] = None

class StateManager:
    """Singleton to manage application state and event broadcasting."""
    def __init__(self):
        self.packet_log: deque = deque(maxlen=2000)
        self.subscribers: List[asyncio.Queue] = []
        self.active_proxies: Dict[int, ProxyConfig] = {}
        self.active_connections: Dict[str, dict] = {}

    def register_proxy(self, config: ProxyConfig):
        self.active_proxies[config.local_port] = config

    def log_packet(self, proxy_port: int, direction: str, data: bytes, conn_id: str):
        config = self.active_proxies.get(proxy_port)
        if not config:
            return

        name = config.name
        
        # Decode logic
        semantic = ""
        if config.protocol == "hamlib":
            semantic = HamlibParser.decode(data)
        
        event = PacketEvent(
            id=str(uuid.uuid4()),
            proxy_name=name,
            direction=direction,
            data_hex=data.hex(' '),
            data_str=data.decode('utf-8', errors='replace'),
            semantic=semantic,
            timestamp=time.time(),
            connection_id=conn_id
        )

        self.packet_log.append(event)
        self.broadcast(event)

    def broadcast(self, event):
        data = asdict(event)
        for q in self.subscribers:
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                pass  # Drop packet if subscriber is too slow

    async def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=100)
        self.subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self.subscribers:
            self.subscribers.remove(q)

state_manager = StateManager()

class TCPProxy:
    def __init__(self, config: ProxyConfig):
        self.config = config
        self.server = None

    async def start(self):
        self.server = await asyncio.start_server(
            self.handle_client, '0.0.0.0', self.config.local_port
        )
        state_manager.register_proxy(self.config)
        logger.info(f"Proxy '{self.config.name}' listening on {self.config.local_port} -> {self.config.target_host}:{self.config.target_port}")
        
        # Keep serving in the background
        self.serve_task = asyncio.create_task(self.server.serve_forever())

    async def close(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        if hasattr(self, 'serve_task'):
            self.serve_task.cancel()
            try:
                await self.serve_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Proxy '{self.config.name}' stopped")

    async def handle_client(self, client_reader, client_writer):
        conn_id = str(uuid.uuid4())[:8]
        peer = client_writer.get_extra_info('peername')
        logger.info(f"[{self.config.name}] New connection from {peer}")
        
        try:
            remote_reader, remote_writer = await asyncio.open_connection(
                self.config.target_host, self.config.target_port
            )
        except Exception as e:
            logger.error(f"Failed to connect to target: {e}")
            client_writer.close()
            return

        async def pipe(reader, writer, direction):
            try:
                while True:
                    data = await reader.read(4096)
                    if not data:
                        break
                    
                    # Log packet
                    state_manager.log_packet(self.config.local_port, direction, data, conn_id)
                    
                    writer.write(data)
                    await writer.drain()
            except Exception as e:
                logger.debug(f"Connection closed/error: {e}")
            finally:
                writer.close()

        # Run pipes bi-directionally
        await asyncio.gather(
            pipe(client_reader, remote_writer, "TX"),  # Client -> Target
            pipe(remote_reader, client_writer, "RX"),  # Target -> Client
            return_exceptions=True
        )

class ProxyEngine:
    def __init__(self):
        self.proxies: List[TCPProxy] = []
        self._monitor_task = None

    async def add_proxy(self, local_port: int, target_host: str, target_port: int, name: str, protocol: str = "raw"):
        config = ProxyConfig(local_port, target_host, target_port, name, protocol)
        proxy = TCPProxy(config)
        await proxy.start()
        self.proxies.append(proxy)
        # Trigger an immediate health check for this proxy (optional, or wait for loop)
        return f"Proxy '{name}' started on port {local_port}"

    async def remove_proxy(self, local_port: int):
        for proxy in self.proxies:
            if proxy.config.local_port == local_port:
                await proxy.close()
                self.proxies.remove(proxy)
                if local_port in state_manager.active_proxies:
                    del state_manager.active_proxies[local_port]
                return f"Proxy on port {local_port} stopped"
        raise ValueError(f"No proxy found on port {local_port}")

    async def stop_monitor(self):
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            except RuntimeError:
                # Task might be in another loop
                pass
            self._monitor_task = None

    async def stop_all_proxies(self):
        logger.info("Stopping all proxies...")
        if not self.proxies:
            return
            
        await asyncio.gather(*(p.close() for p in self.proxies), return_exceptions=True)
        self.proxies.clear()
        state_manager.active_proxies.clear()
        logger.info("All proxies stopped.")

    async def shutdown(self):
        await self.stop_monitor()
        await self.stop_all_proxies()
        logger.info("Engine shutdown complete.")

    async def start_monitor(self):
        if self._monitor_task is None:
            self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self):
        logger.info("Starting health monitor loop")
        while True:
            try:
                for proxy in self.proxies:
                    await self._check_proxy_health(proxy)
                await asyncio.sleep(5)  # Poll every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(5)

    async def _check_proxy_health(self, proxy: TCPProxy):
        host = proxy.config.target_host
        port = proxy.config.target_port
        
        status = "offline"
        error_msg = None
        
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=2.0
            )
            writer.close()
            await writer.wait_closed()
            status = "online"
        except Exception as e:
            status = "offline"
            error_msg = str(e)
            
        # Check if state changed
        if proxy.config.status != status or proxy.config.error_msg != error_msg:
            proxy.config.status = status
            proxy.config.error_msg = error_msg
            
            # Broadcast update
            event = StatusEvent(
                local_port=proxy.config.local_port,
                status=status,
                error_msg=error_msg
            )
            state_manager.broadcast(event)

engine = ProxyEngine()