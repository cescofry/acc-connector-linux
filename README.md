# ACC Connector (Linux / Python)

A terminal-based tool for Linux that advertises Assetto Corsa Competizione (ACC) dedicated servers to the game's built-in server browser via UDP discovery.

This is a Python port of the [original ACC Connector](https://github.com/lonemeow/acc-connector) for Windows. It replicates the same discovery protocol and URI format but uses a terminal UI (TUI) instead of a native GUI window.

---

## How it works

ACC's server browser discovers LAN servers by broadcasting a 6-byte UDP packet on port 8999. ACC Connector listens on that port, parses the request, and replies with the details of each configured server (name, IP, port). The game then lists those servers in its browser as if they were discovered natively on the network.

This is useful when ACC is running on a machine that cannot see the server by broadcast — for example when the server is on a different subnet, a VPN, or a remote host.

---

## Requirements

- Python 3.10 or later
- The `textual` library (see `requirements.txt`)

Install dependencies:

Install via curl (installs the `acc-connector` command globally):

```bash
curl -sSL https://raw.githubusercontent.com/cescofry/acc-connector-linux/main/install.sh | bash
```

Or install manually:

```bash
pip install .
```

---

## Running

Start the TUI:

```bash
acc-connector
```

Start with a server pre-loaded from a URI:

```bash
acc-connector "acc-connect://hostname:9911?name=My+Server&persistent=true"
```

The URI format is identical to the Windows version's registered URI handler, so links shared from Windows users work directly as CLI arguments here.

---

## URI format

```
acc-connect://<host>:<port>?name=<display name>&persistent=<true|false>
```

| Parameter    | Required | Default | Description                                  |
|-------------|----------|---------|----------------------------------------------|
| `host`      | yes      | —       | Hostname or IP address of the ACC server     |
| `port`      | yes      | 9911    | TCP port the ACC server listens on           |
| `name`      | no       | —       | Human-readable label shown in the server list |
| `persistent`| no       | `true`  | Whether to save the server between sessions  |

---

## TUI overview

When running, the interface shows a table of configured servers with three columns:

| Column  | Description                                      |
|---------|--------------------------------------------------|
| Name    | Display name, or `host:port` if no name was set  |
| Address | `host:port`                                      |
| Saved   | ✦ mark if the server is persisted across sessions |

### Controls

| Key / Button       | Action                             |
|--------------------|------------------------------------|
| `a` / Add button   | Open the Add Server dialog         |
| `Delete` / Remove  | Remove the selected server         |
| `t` / Discovery button | Toggle the UDP discovery listener |
| `q`                | Quit                               |
| `Escape`           | Cancel the Add Server dialog       |

### Adding a server

Press `a` or click **Add** to open a dialog with the following fields:

- **Name** (optional) — label shown in ACC's browser and in the table
- **Address** — hostname or IP of the ACC server (resolved at add time to validate)
- **Port** — default is `9911`
- **Persistent** — if checked, the server is saved to disk and restored on next launch

### Discovery toggle

The **Discovery** button starts or stops the UDP listener on port 8999. The button label and colour reflect the current state (green = ON, red = OFF). Discovery must be ON for ACC to find the servers.

Binding port 8999 requires no special privileges on most Linux systems, but if the port is already in use an error is shown in the status bar.

---

## Configuration and data files

All files are stored under `~/.config/acc-connector/`.

| File           | Purpose                                      |
|----------------|----------------------------------------------|
| `servers.json` | Saved server list (one URI per entry)        |
| `app.log`      | Debug log for the current and past sessions  |

`servers.json` contains a JSON array of `acc-connect://` URIs. Only servers marked as persistent are written here. Example:

```json
[
  "acc-connect://192.168.1.50:9911?name=Home+Server&persistent=true",
  "acc-connect://race.example.com:9911?name=Online+League&persistent=true"
]
```

---

## Discovery protocol details

The tool implements ACC's LAN discovery protocol over UDP.

**Request** (sent by ACC, 6 bytes):

| Bytes | Value      | Description          |
|-------|------------|----------------------|
| 0–1   | `0xBF 0x48`| Magic header         |
| 2–5   | uint32 LE  | Discovery ID (echoed in response) |

**Response** (sent by this tool, variable length):

| Bytes         | Value         | Description                            |
|---------------|---------------|----------------------------------------|
| 0             | `0xC0`        | Response header byte                   |
| 1             | uint8         | Server name length in characters       |
| 2 … 2+N*4−1  | UTF-32-LE     | Server name (4 bytes per character)    |
| next 2        | `0x00 0x01`   | Constant                               |
| next 2        | uint16 BE     | Server port                            |
| next 4        | uint32 LE     | Discovery ID (echoed from request)     |
| last 1        | `0xFA`        | Footer byte                            |

One response packet is sent per configured server.

---

## Differences from the Windows version

| Feature              | Windows version          | This (Linux/Python)                        |
|----------------------|--------------------------|--------------------------------------------|
| UI                   | Native GUI               | Terminal UI (via `textual`)                |
| URI handler          | Registered OS handler    | CLI argument (`acc-connector "<uri>"`)     |
| Platform             | Windows only             | Linux (and any OS with Python 3.10+)       |
| Config location      | Windows AppData          | `~/.config/acc-connector/`                |
| Discovery protocol   | Identical                | Identical                                  |
| URI format           | Identical                | Identical                                  |
