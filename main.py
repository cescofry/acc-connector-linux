#!/usr/bin/env python3
"""ACC Connector — Python/Linux port.

Usage:
  python main.py
  python main.py "acc-connect://hostname:9911?name=My+Server&persistent=true"
"""
from __future__ import annotations

import sys

import config
from models import ServerInfo
from tui import ACCConnectorApp


def main() -> None:
    config.setup_logging()
    servers = config.load_servers()

    # Accept an acc-connect:// URI as a CLI argument (same as Windows URI handler)
    for arg in sys.argv[1:]:
        if arg.startswith("acc-connect://"):
            try:
                srv = ServerInfo.from_uri(arg)
                if not any(s.host == srv.host and s.port == srv.port for s in servers):
                    servers.append(srv)
                    if srv.persistent:
                        config.save_servers(servers)
            except Exception as e:
                print(f"Invalid URI: {e}", file=sys.stderr)

    app = ACCConnectorApp(servers)
    app.run()


if __name__ == "__main__":
    main()
