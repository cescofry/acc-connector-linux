from __future__ import annotations

import asyncio
import socket

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
)

import config
from discovery import DiscoveryServer
from models import ServerInfo

PERSISTENT_MARK = "\u2746"  # ✦


class AddServerModal(ModalScreen[ServerInfo | None]):
    BINDINGS = [Binding("escape", "dismiss_none", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Add Server", id="dialog-title")
            yield Label("Name (optional)")
            yield Input(placeholder="My Race Server", id="input-name")
            yield Label("Address")
            yield Input(placeholder="hostname or IP", id="input-address")
            yield Label("Port")
            yield Input(placeholder="9911", id="input-port", value="9911")
            yield Checkbox("Persistent (saved between sessions)", value=True, id="input-persistent")
            with Horizontal(id="dialog-buttons"):
                yield Button("Add", variant="primary", id="btn-add")
                yield Button("Cancel", id="btn-cancel")

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#btn-cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#btn-add")
    def add(self) -> None:
        name = self.query_one("#input-name", Input).value.strip()
        address = self.query_one("#input-address", Input).value.strip()
        port_str = self.query_one("#input-port", Input).value.strip()
        persistent = self.query_one("#input-persistent", Checkbox).value

        if not address:
            self.notify("Address is required.", severity="error")
            return
        try:
            port = int(port_str)
            if not (0 <= port <= 65535):
                raise ValueError
        except ValueError:
            self.notify("Port must be 0–65535.", severity="error")
            return
        try:
            socket.gethostbyname(address)
        except socket.gaierror:
            self.notify(f"Cannot resolve '{address}'.", severity="error")
            return

        self.dismiss(ServerInfo(host=address, port=port, name=name, persistent=persistent))


class ACCConnectorApp(App):
    CSS = """
    Screen {
        background: $surface;
    }
    #main-container {
        height: 1fr;
        padding: 1 2;
    }
    #toolbar {
        height: 3;
        align: right middle;
        margin-bottom: 1;
    }
    #server-table {
        height: 1fr;
        border: solid $primary;
    }
    #action-bar {
        height: 3;
        margin-top: 1;
        align: left middle;
    }
    #btn-toggle {
        margin-left: 1;
    }
    #status-bar {
        height: 1;
        color: $text-muted;
        padding: 0 1;
    }
    #dialog {
        background: $panel;
        border: double $primary;
        padding: 2 4;
        width: 60;
        height: auto;
    }
    #dialog-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #dialog-buttons {
        margin-top: 1;
        align: right middle;
    }
    """

    BINDINGS = [
        Binding("a", "add_server", "Add"),
        Binding("delete", "remove_server", "Remove"),
        Binding("t", "toggle_discovery", "Toggle Discovery"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, initial_servers: list[ServerInfo]) -> None:
        super().__init__()
        self._servers: list[ServerInfo] = initial_servers
        self._discovery = DiscoveryServer()
        self._discovery.servers = self._servers

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            with Horizontal(id="toolbar"):
                yield Button("Discovery: OFF", id="btn-toggle", variant="error")
            yield DataTable(id="server-table", cursor_type="row")
            with Horizontal(id="action-bar"):
                yield Button("Add", id="btn-add", variant="success")
                yield Button("Remove", id="btn-remove", variant="warning")
            yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_column("Name", width=32)
        table.add_column("Address", width=24)
        table.add_column("Saved", width=6)
        for srv in self._servers:
            self._add_row(table, srv)

    def _add_row(self, table: DataTable, srv: ServerInfo) -> None:
        table.add_row(
            srv.display_name(),
            f"{srv.host}:{srv.port}",
            PERSISTENT_MARK if srv.persistent else "",
        )

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-bar", Static).update(msg)

    @on(Button.Pressed, "#btn-add")
    @work
    async def action_add_server(self) -> None:
        result = await self.push_screen_wait(AddServerModal())
        if result is None:
            return
        self._servers.append(result)
        self._add_row(self.query_one(DataTable), result)
        if result.persistent:
            config.save_servers(self._servers)
        self._set_status(f"Added {result.display_name()}")

    @on(Button.Pressed, "#btn-remove")
    def action_remove_server(self) -> None:
        table = self.query_one(DataTable)
        if not self._servers:
            return
        idx = table.cursor_row
        if idx < 0 or idx >= len(self._servers):
            return
        removed = self._servers.pop(idx)
        row_keys = list(table.rows.keys())
        if idx < len(row_keys):
            table.remove_row(row_keys[idx])
        config.save_servers(self._servers)
        self._set_status(f"Removed {removed.display_name()}")

    @on(Button.Pressed, "#btn-toggle")
    async def action_toggle_discovery(self) -> None:
        btn = self.query_one("#btn-toggle", Button)
        if self._discovery.running:
            self._discovery.stop()
            btn.label = "Discovery: OFF"
            btn.variant = "error"
            self._set_status("Discovery server stopped.")
        else:
            try:
                await self._discovery.start()
                btn.label = "Discovery: ON "
                btn.variant = "success"
                self._set_status(f"Listening for ACC on UDP port 8999 ({len(self._servers)} server(s) configured)")
            except OSError as e:
                self._set_status(f"Failed to start: {e}")

    async def on_unmount(self) -> None:
        self._discovery.stop()
