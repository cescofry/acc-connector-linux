from __future__ import annotations

import asyncio
import logging
import socket

from models import ServerInfo, parse_discovery_request

DISCOVERY_PORT = 8999
log = logging.getLogger(__name__)


class DiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, server: DiscoveryServer) -> None:
        self._server = server
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:  # type: ignore[override]
        self.transport = transport
        sock = transport.get_extra_info("socket")
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        discovery_id = parse_discovery_request(data)
        if discovery_id is None:
            return
        log.debug("Discovery request from %s id=%d", addr, discovery_id)
        for srv in self._server.servers:
            try:
                pkt = srv.to_packet(discovery_id)
                self.transport.sendto(pkt, addr)
                log.debug("Sent response for %s to %s", srv.display_name(), addr)
            except Exception:
                log.exception("Failed to send response for %s", srv.display_name())

    def error_received(self, exc: Exception) -> None:
        log.error("UDP error: %s", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        pass


class DiscoveryServer:
    def __init__(self) -> None:
        self.servers: list[ServerInfo] = []
        self._transport: asyncio.DatagramTransport | None = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    async def start(self) -> None:
        if self._running:
            return
        loop = asyncio.get_running_loop()
        try:
            transport, _ = await loop.create_datagram_endpoint(
                lambda: DiscoveryProtocol(self),
                local_addr=("0.0.0.0", DISCOVERY_PORT),
                allow_broadcast=True,
            )
            self._transport = transport
            self._running = True
            log.info("Discovery server listening on UDP port %d", DISCOVERY_PORT)
        except OSError as e:
            log.error("Failed to bind port %d: %s", DISCOVERY_PORT, e)
            raise

    def stop(self) -> None:
        if self._transport:
            self._transport.close()
            self._transport = None
        self._running = False
        log.info("Discovery server stopped")
