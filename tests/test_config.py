from __future__ import annotations

import json

import pytest

import config
from models import ServerInfo


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "acc-connector"
    monkeypatch.setattr(config, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config, "SERVERS_FILE", cfg_dir / "servers.json")
    monkeypatch.setattr(config, "LOG_FILE", cfg_dir / "app.log")
    return cfg_dir


class TestEnsureConfigDir:
    def test_creates_directory(self, config_dir):
        assert not config_dir.exists()
        config.ensure_config_dir()
        assert config_dir.exists()

    def test_idempotent(self, config_dir):
        config.ensure_config_dir()
        config.ensure_config_dir()
        assert config_dir.exists()


class TestLoadServers:
    def test_returns_empty_when_file_missing(self, config_dir):
        assert config.load_servers() == []

    def test_loads_single_server(self, config_dir):
        config_dir.mkdir(parents=True)
        uris = ["acc-connect://192.168.1.1:9911?persistent=true&name=Race"]
        (config_dir / "servers.json").write_text(json.dumps(uris))
        servers = config.load_servers()
        assert len(servers) == 1
        assert servers[0].host == "192.168.1.1"
        assert servers[0].port == 9911
        assert servers[0].name == "Race"

    def test_loads_multiple_servers(self, config_dir):
        config_dir.mkdir(parents=True)
        uris = [
            "acc-connect://10.0.0.1:9911?persistent=true",
            "acc-connect://10.0.0.2:9912?persistent=true",
        ]
        (config_dir / "servers.json").write_text(json.dumps(uris))
        servers = config.load_servers()
        assert len(servers) == 2

    def test_loads_persistent_flag(self, config_dir):
        config_dir.mkdir(parents=True)
        uris = ["acc-connect://10.0.0.1:9911?persistent=false"]
        (config_dir / "servers.json").write_text(json.dumps(uris))
        servers = config.load_servers()
        assert servers[0].persistent is False

    def test_returns_empty_on_invalid_json(self, config_dir):
        config_dir.mkdir(parents=True)
        (config_dir / "servers.json").write_text("not valid json {{")
        assert config.load_servers() == []

    def test_returns_empty_list_when_file_is_empty_array(self, config_dir):
        config_dir.mkdir(parents=True)
        (config_dir / "servers.json").write_text("[]")
        assert config.load_servers() == []


class TestSaveServers:
    def test_saves_persistent_servers_only(self, config_dir):
        servers = [
            ServerInfo(host="10.0.0.1", port=9911, persistent=True),
            ServerInfo(host="10.0.0.2", port=9912, persistent=False),
        ]
        config.save_servers(servers)
        data = json.loads((config_dir / "servers.json").read_text())
        assert len(data) == 1
        assert "10.0.0.1" in data[0]

    def test_non_persistent_server_excluded(self, config_dir):
        servers = [ServerInfo(host="10.0.0.1", port=9911, persistent=False)]
        config.save_servers(servers)
        data = json.loads((config_dir / "servers.json").read_text())
        assert data == []

    def test_saves_empty_list(self, config_dir):
        config.save_servers([])
        data = json.loads((config_dir / "servers.json").read_text())
        assert data == []

    def test_creates_config_dir_if_missing(self, config_dir):
        assert not config_dir.exists()
        config.save_servers([])
        assert config_dir.exists()

    def test_written_values_are_uris(self, config_dir):
        servers = [ServerInfo(host="10.0.0.1", port=9911, persistent=True)]
        config.save_servers(servers)
        data = json.loads((config_dir / "servers.json").read_text())
        assert data[0].startswith("acc-connect://")

    def test_round_trip_with_name(self, config_dir):
        original = [
            ServerInfo(host="10.0.0.1", port=9911, name="Server A", persistent=True),
        ]
        config.save_servers(original)
        loaded = config.load_servers()
        assert len(loaded) == 1
        assert loaded[0].host == original[0].host
        assert loaded[0].port == original[0].port
        assert loaded[0].name == original[0].name
        assert loaded[0].persistent == original[0].persistent

    def test_round_trip_multiple_servers(self, config_dir):
        original = [
            ServerInfo(host="10.0.0.1", port=9911, name="A", persistent=True),
            ServerInfo(host="10.0.0.2", port=9912, name="B", persistent=True),
        ]
        config.save_servers(original)
        loaded = config.load_servers()
        assert len(loaded) == 2
        hosts = {s.host for s in loaded}
        assert hosts == {"10.0.0.1", "10.0.0.2"}
