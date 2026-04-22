from __future__ import annotations

import socket
import struct
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlencode, urlparse

DISCOVERY_MAGIC = b"\xbf\x48"
RESPONSE_HEADER = b"\xc0"
RESPONSE_CONST = b"\x00\x01"
RESPONSE_FOOTER = b"\xfa"
MAX_NAME_LEN = 256


@dataclass
class ServerInfo:
    host: str
    port: int
    name: str = ""
    persistent: bool = True

    def resolve_ip(self) -> str:
        return socket.gethostbyname(self.host)

    def display_name(self) -> str:
        return self.name if self.name else f"{self.host}:{self.port}"

    def to_packet(self, discovery_id: int) -> bytes:
        name = (self.name or f"{self.host}:{self.port}")[:MAX_NAME_LEN]
        name_utf32 = name.encode("utf-32-le")
        name_len = len(name)
        ip_bytes = socket.inet_aton(self.resolve_ip())
        # Response: [0xC0][name_len][name_utf32][0x00][0x01][port_be][discovery_id_le][0xFA]
        return (
            RESPONSE_HEADER
            + bytes([name_len])
            + name_utf32
            + RESPONSE_CONST
            + struct.pack("!H", self.port)
            + struct.pack("<I", discovery_id)
            + RESPONSE_FOOTER
        )

    def to_uri(self) -> str:
        params: dict[str, str] = {"persistent": str(self.persistent).lower()}
        if self.name:
            params["name"] = self.name
        return f"acc-connect://{self.host}:{self.port}?{urlencode(params)}"

    @classmethod
    def from_uri(cls, uri: str) -> ServerInfo:
        parsed = urlparse(uri)
        host = parsed.hostname or ""
        port = parsed.port or 9911
        qs = parse_qs(parsed.query)
        name = qs.get("name", [""])[0]
        persistent_str = qs.get("persistent", ["true"])[0].lower()
        persistent = persistent_str not in ("false", "0", "no")
        return cls(host=host, port=port, name=name, persistent=persistent)


def parse_discovery_request(data: bytes) -> int | None:
    if len(data) == 6 and data[:2] == DISCOVERY_MAGIC:
        return struct.unpack("<I", data[2:6])[0]
    return None
