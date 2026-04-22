from __future__ import annotations

import json
import logging
from pathlib import Path

from models import ServerInfo

CONFIG_DIR = Path.home() / ".config" / "acc-connector"
SERVERS_FILE = CONFIG_DIR / "servers.json"
LOG_FILE = CONFIG_DIR / "app.log"

log = logging.getLogger(__name__)


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging() -> None:
    ensure_config_dir()
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(),
        ],
    )


def load_servers() -> list[ServerInfo]:
    if not SERVERS_FILE.exists():
        return []
    try:
        uris = json.loads(SERVERS_FILE.read_text())
        return [ServerInfo.from_uri(u) for u in uris]
    except Exception:
        log.exception("Failed to load servers from %s", SERVERS_FILE)
        return []


def save_servers(servers: list[ServerInfo]) -> None:
    ensure_config_dir()
    persistent = [s for s in servers if s.persistent]
    uris = [s.to_uri() for s in persistent]
    SERVERS_FILE.write_text(json.dumps(uris, indent=2))
