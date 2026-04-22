from __future__ import annotations

import socket
import struct
from unittest.mock import MagicMock, call

import pytest

from discovery import DiscoveryProtocol, DiscoveryServer
from models import DISCOVERY_MAGIC, ServerInfo


def _make_request(discovery_id: int) -> bytes:
    return DISCOVERY_MAGIC + struct.pack("<I", discovery_id)


def _make_protocol(servers=None) -> tuple[DiscoveryProtocol, MagicMock]:
    ds = DiscoveryServer()
    ds.servers = servers or []
    protocol = DiscoveryProtocol(ds)
    mock_transport = MagicMock()
    protocol.transport = mock_transport
    return protocol, mock_transport


class TestDiscoveryServerState:
    def test_not_running_initially(self):
        assert DiscoveryServer().running is False

    def test_servers_empty_initially(self):
        assert DiscoveryServer().servers == []

    def test_stop_when_not_started_is_noop(self):
        server = DiscoveryServer()
        server.stop()
        assert server.running is False

    def test_stop_clears_running_flag(self):
        server = DiscoveryServer()
        server._running = True
        server._transport = MagicMock()
        server.stop()
        assert server.running is False

    def test_stop_closes_transport(self):
        server = DiscoveryServer()
        mock_transport = MagicMock()
        server._transport = mock_transport
        server._running = True
        server.stop()
        mock_transport.close.assert_called_once()

    def test_stop_clears_transport_reference(self):
        server = DiscoveryServer()
        server._transport = MagicMock()
        server._running = True
        server.stop()
        assert server._transport is None


class TestDiscoveryProtocolConnectionMade:
    def test_stores_transport(self):
        protocol, _ = _make_protocol()
        mock_transport = MagicMock()
        mock_transport.get_extra_info.return_value = MagicMock()
        protocol.transport = None
        protocol.connection_made(mock_transport)
        assert protocol.transport is mock_transport

    def test_sets_broadcast_socket_option(self):
        protocol, _ = _make_protocol()
        mock_transport = MagicMock()
        mock_sock = MagicMock()
        mock_transport.get_extra_info.return_value = mock_sock
        protocol.connection_made(mock_transport)
        mock_sock.setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def test_sets_reuseaddr_socket_option(self):
        protocol, _ = _make_protocol()
        mock_transport = MagicMock()
        mock_sock = MagicMock()
        mock_transport.get_extra_info.return_value = mock_sock
        protocol.connection_made(mock_transport)
        mock_sock.setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


class TestDiscoveryProtocolDatagramReceived:
    def test_ignores_invalid_magic(self):
        protocol, transport = _make_protocol()
        protocol.datagram_received(b"\x00\x00\x00\x00\x00\x00", ("127.0.0.1", 12345))
        transport.sendto.assert_not_called()

    def test_ignores_too_short_packet(self):
        protocol, transport = _make_protocol()
        protocol.datagram_received(DISCOVERY_MAGIC, ("127.0.0.1", 12345))
        transport.sendto.assert_not_called()

    def test_ignores_too_long_packet(self):
        protocol, transport = _make_protocol()
        protocol.datagram_received(_make_request(1) + b"\x00", ("127.0.0.1", 12345))
        transport.sendto.assert_not_called()

    def test_no_servers_sends_nothing(self):
        protocol, transport = _make_protocol(servers=[])
        protocol.datagram_received(_make_request(1), ("127.0.0.1", 54321))
        transport.sendto.assert_not_called()

    def test_sends_one_packet_per_server(self):
        servers = [
            ServerInfo(host="127.0.0.1", port=9911, name="A"),
            ServerInfo(host="127.0.0.1", port=9912, name="B"),
        ]
        protocol, transport = _make_protocol(servers)
        protocol.datagram_received(_make_request(42), ("127.0.0.1", 54321))
        assert transport.sendto.call_count == 2

    def test_sends_to_originating_address(self):
        servers = [ServerInfo(host="127.0.0.1", port=9911, name="Test")]
        protocol, transport = _make_protocol(servers)
        addr = ("192.168.1.100", 54321)
        protocol.datagram_received(_make_request(1), addr)
        _, sent_addr = transport.sendto.call_args[0]
        assert sent_addr == addr

    def test_sent_packet_contains_discovery_id(self):
        discovery_id = 0xABCD1234
        servers = [ServerInfo(host="127.0.0.1", port=9911, name="T")]
        protocol, transport = _make_protocol(servers)
        protocol.datagram_received(_make_request(discovery_id), ("127.0.0.1", 54321))
        sent_pkt, _ = transport.sendto.call_args[0]
        # discovery_id is 4 bytes LE near the end: footer is last, id before that
        id_bytes = sent_pkt[-5:-1]
        assert struct.unpack("<I", id_bytes)[0] == discovery_id

    def test_handles_sendto_error_without_raising(self):
        servers = [ServerInfo(host="127.0.0.1", port=9911, name="Test")]
        protocol, transport = _make_protocol(servers)
        transport.sendto.side_effect = OSError("Network error")
        # must not propagate the exception
        protocol.datagram_received(_make_request(1), ("127.0.0.1", 54321))

    def test_continues_after_one_server_fails(self):
        servers = [
            ServerInfo(host="127.0.0.1", port=9911, name="Good1"),
            ServerInfo(host="127.0.0.1", port=9912, name="Good2"),
        ]
        protocol, transport = _make_protocol(servers)
        # fail only on first call
        transport.sendto.side_effect = [OSError("fail"), None]
        protocol.datagram_received(_make_request(1), ("127.0.0.1", 54321))
        assert transport.sendto.call_count == 2


class TestDiscoveryProtocolErrorReceived:
    def test_does_not_raise(self):
        protocol, _ = _make_protocol()
        protocol.error_received(OSError("UDP error"))
