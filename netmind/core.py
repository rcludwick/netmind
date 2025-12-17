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

@dataclass
class ProxyConfig:
    local_port: int
    target_host: str
    target_port: int
    name: str
    protocol: str = "raw"  # raw, hamlib

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

    def broadcast(self, event: PacketEvent):
        for q in self.subscribers:
            try:
                q.put_nowait(asdict(event))
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
        asyncio.create_task(self.server.serve_forever())

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

    async def add_proxy(self, local_port: int, target_host: str, target_port: int, name: str, protocol: str = "raw"):
        config = ProxyConfig(local_port, target_host, target_port, name, protocol)
        proxy = TCPProxy(config)
        await proxy.start()
        self.proxies.append(proxy)
        return f"Proxy '{name}' started on port {local_port}"

engine = ProxyEngine()