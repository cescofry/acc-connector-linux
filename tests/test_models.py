from __future__ import annotations

import socket
import struct

import pytest

from models import (
    DISCOVERY_MAGIC,
    MAX_NAME_LEN,
    RESPONSE_CONST,
    RESPONSE_FOOTER,
    RESPONSE_HEADER,
    ServerInfo,
    parse_discovery_request,
)


class TestServerInfoDefaults:
    def test_default_name_is_empty(self):
        srv = ServerInfo(host="127.0.0.1", port=9911)
        assert srv.name == ""

    def test_default_persistent_is_true(self):
        srv = ServerInfo(host="127.0.0.1", port=9911)
        assert srv.persistent is True


class TestDisplayName:
    def test_returns_name_when_set(self):
        srv = ServerInfo(host="192.168.1.1", port=9911, name="Race Server")
        assert srv.display_name() == "Race Server"

    def test_returns_host_port_when_name_empty(self):
        srv = ServerInfo(host="192.168.1.1", port=9911, name="")
        assert srv.display_name() == "192.168.1.1:9911"

    def test_returns_host_port_when_name_default(self):
        srv = ServerInfo(host="10.0.0.1", port=12345)
        assert srv.display_name() == "10.0.0.1:12345"


class TestToUri:
    def test_scheme_prefix(self):
        srv = ServerInfo(host="192.168.1.1", port=9911)
        assert srv.to_uri().startswith("acc-connect://")

    def test_host_and_port_in_authority(self):
        srv = ServerInfo(host="192.168.1.1", port=9911)
        assert "192.168.1.1:9911" in srv.to_uri()

    def test_name_included_when_set(self):
        srv = ServerInfo(host="192.168.1.1", port=9911, name="Test")
        assert "name=Test" in srv.to_uri()

    def test_name_omitted_when_empty(self):
        srv = ServerInfo(host="192.168.1.1", port=9911)
        assert "name=" not in srv.to_uri()

    def test_persistent_true(self):
        srv = ServerInfo(host="192.168.1.1", port=9911, persistent=True)
        assert "persistent=true" in srv.to_uri()

    def test_persistent_false(self):
        srv = ServerInfo(host="192.168.1.1", port=9911, persistent=False)
        assert "persistent=false" in srv.to_uri()


class TestFromUri:
    def test_parses_host(self):
        srv = ServerInfo.from_uri("acc-connect://192.168.1.1:9911?persistent=true")
        assert srv.host == "192.168.1.1"

    def test_parses_port(self):
        srv = ServerInfo.from_uri("acc-connect://192.168.1.1:9911?persistent=true")
        assert srv.port == 9911

    def test_parses_name(self):
        srv = ServerInfo.from_uri("acc-connect://192.168.1.1:9911?name=My+Server&persistent=true")
        assert srv.name == "My Server"

    def test_empty_name_when_absent(self):
        srv = ServerInfo.from_uri("acc-connect://192.168.1.1:9911?persistent=true")
        assert srv.name == ""

    def test_persistent_true(self):
        srv = ServerInfo.from_uri("acc-connect://192.168.1.1:9911?persistent=true")
        assert srv.persistent is True

    def test_persistent_false_string(self):
        srv = ServerInfo.from_uri("acc-connect://192.168.1.1:9911?persistent=false")
        assert srv.persistent is False

    def test_persistent_zero(self):
        srv = ServerInfo.from_uri("acc-connect://192.168.1.1:9911?persistent=0")
        assert srv.persistent is False

    def test_persistent_no(self):
        srv = ServerInfo.from_uri("acc-connect://192.168.1.1:9911?persistent=no")
        assert srv.persistent is False

    def test_persistent_true_by_default(self):
        srv = ServerInfo.from_uri("acc-connect://192.168.1.1:9911")
        assert srv.persistent is True

    def test_default_port_when_absent(self):
        srv = ServerInfo.from_uri("acc-connect://192.168.1.1?persistent=true")
        assert srv.port == 9911

    def test_round_trip_with_name(self):
        original = ServerInfo(host="10.0.0.5", port=12345, name="Race Server", persistent=True)
        restored = ServerInfo.from_uri(original.to_uri())
        assert restored.host == original.host
        assert restored.port == original.port
        assert restored.name == original.name
        assert restored.persistent == original.persistent

    def test_round_trip_no_name_not_persistent(self):
        original = ServerInfo(host="10.0.0.5", port=12345, persistent=False)
        restored = ServerInfo.from_uri(original.to_uri())
        assert restored.host == original.host
        assert restored.port == original.port
        assert restored.name == original.name
        assert restored.persistent == original.persistent


class TestResolveIp:
    def test_ip_address_returns_same(self):
        srv = ServerInfo(host="127.0.0.1", port=9911)
        assert srv.resolve_ip() == "127.0.0.1"

    def test_localhost_resolves_to_ipv4(self):
        srv = ServerInfo(host="localhost", port=9911)
        assert srv.resolve_ip() == "127.0.0.1"

    def test_unknown_host_raises(self):
        srv = ServerInfo(host="this-host-does-not.exist.invalid", port=9911)
        with pytest.raises(socket.gaierror):
            srv.resolve_ip()


class TestToPacket:
    def _offsets(self, name: str) -> dict:
        name_len = len(name)
        name_end = 2 + name_len * 4
        const_end = name_end + 2
        port_end = const_end + 2
        id_end = port_end + 4
        return {
            "name_start": 2,
            "name_end": name_end,
            "const_start": name_end,
            "const_end": const_end,
            "port_start": const_end,
            "port_end": port_end,
            "id_start": port_end,
            "id_end": id_end,
            "footer_idx": id_end,
        }

    def test_starts_with_response_header(self):
        pkt = ServerInfo(host="127.0.0.1", port=9911, name="T").to_packet(1)
        assert pkt[0:1] == RESPONSE_HEADER

    def test_ends_with_footer(self):
        pkt = ServerInfo(host="127.0.0.1", port=9911, name="T").to_packet(1)
        assert pkt[-1:] == RESPONSE_FOOTER

    def test_name_length_byte(self):
        name = "Hi"
        pkt = ServerInfo(host="127.0.0.1", port=9911, name=name).to_packet(1)
        assert pkt[1] == len(name)

    def test_name_encoded_utf32le(self):
        name = "ABC"
        pkt = ServerInfo(host="127.0.0.1", port=9911, name=name).to_packet(1)
        off = self._offsets(name)
        assert pkt[off["name_start"]:off["name_end"]] == name.encode("utf-32-le")

    def test_response_const_after_name(self):
        name = "X"
        pkt = ServerInfo(host="127.0.0.1", port=9911, name=name).to_packet(1)
        off = self._offsets(name)
        assert pkt[off["const_start"]:off["const_end"]] == RESPONSE_CONST

    def test_port_big_endian(self):
        port = 9911
        name = "T"
        pkt = ServerInfo(host="127.0.0.1", port=port, name=name).to_packet(1)
        off = self._offsets(name)
        assert struct.unpack("!H", pkt[off["port_start"]:off["port_end"]])[0] == port

    def test_discovery_id_little_endian(self):
        discovery_id = 0xDEADBEEF
        name = "T"
        pkt = ServerInfo(host="127.0.0.1", port=9911, name=name).to_packet(discovery_id)
        off = self._offsets(name)
        assert struct.unpack("<I", pkt[off["id_start"]:off["id_end"]])[0] == discovery_id

    def test_no_name_uses_host_port_fallback(self):
        srv = ServerInfo(host="127.0.0.1", port=9911, name="")
        pkt = srv.to_packet(1)
        fallback = "127.0.0.1:9911"
        assert pkt[1] == len(fallback)
        assert pkt[2 : 2 + len(fallback) * 4] == fallback.encode("utf-32-le")

    def test_name_truncated_to_max_len(self):
        long_name = "A" * (MAX_NAME_LEN + 10)
        pkt = ServerInfo(host="127.0.0.1", port=9911, name=long_name).to_packet(1)
        assert pkt[1] == MAX_NAME_LEN

    def test_total_packet_length(self):
        name = "Test"
        pkt = ServerInfo(host="127.0.0.1", port=9911, name=name).to_packet(1)
        # 1 header + 1 name_len + 4*len(name) name_utf32 + 2 const + 2 port + 4 id + 1 footer
        assert len(pkt) == 1 + 1 + len(name) * 4 + 2 + 2 + 4 + 1

    def test_discovery_id_zero(self):
        name = "T"
        pkt = ServerInfo(host="127.0.0.1", port=9911, name=name).to_packet(0)
        off = self._offsets(name)
        assert struct.unpack("<I", pkt[off["id_start"]:off["id_end"]])[0] == 0

    def test_discovery_id_max(self):
        name = "T"
        pkt = ServerInfo(host="127.0.0.1", port=9911, name=name).to_packet(0xFFFFFFFF)
        off = self._offsets(name)
        assert struct.unpack("<I", pkt[off["id_start"]:off["id_end"]])[0] == 0xFFFFFFFF


class TestParseDiscoveryRequest:
    def _make_request(self, discovery_id: int) -> bytes:
        return DISCOVERY_MAGIC + struct.pack("<I", discovery_id)

    def test_valid_request_returns_discovery_id(self):
        assert parse_discovery_request(self._make_request(12345)) == 12345

    def test_zero_discovery_id(self):
        assert parse_discovery_request(self._make_request(0)) == 0

    def test_max_discovery_id(self):
        assert parse_discovery_request(self._make_request(0xFFFFFFFF)) == 0xFFFFFFFF

    def test_wrong_magic_returns_none(self):
        data = b"\x00\x00" + struct.pack("<I", 1)
        assert parse_discovery_request(data) is None

    def test_wrong_first_byte_returns_none(self):
        data = b"\x00\x48" + struct.pack("<I", 1)
        assert parse_discovery_request(data) is None

    def test_wrong_second_byte_returns_none(self):
        data = b"\xbf\x00" + struct.pack("<I", 1)
        assert parse_discovery_request(data) is None

    def test_too_short_returns_none(self):
        assert parse_discovery_request(DISCOVERY_MAGIC + b"\x01\x00") is None

    def test_too_long_returns_none(self):
        assert parse_discovery_request(self._make_request(1) + b"\x00") is None

    def test_empty_returns_none(self):
        assert parse_discovery_request(b"") is None
