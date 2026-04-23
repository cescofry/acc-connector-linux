# ACC Connector TUI (Universal)

A terminal-based tool that advertises Assetto Corsa Competizione (ACC) dedicated servers to the game's built-in server browser via UDP discovery. Works on **Linux, macOS, and Windows**.

This is a Python port of the [original ACC Connector](https://github.com/lonemeow/acc-connector) for Windows. It replicates the same discovery protocol and URI format but uses a terminal UI (TUI) instead of a native GUI window.

---

## Platform support

| Platform | Supported | URI handler auto-registered | Notes |
|----------|-----------|----------------------------|-------|
| Linux    | Yes       | Yes (via install script)   | All install methods work |
| macOS    | Partial   | No — manual step required  | See macOS notes below |
| Windows  | Partial   | No — manual step required  | See Windows notes below |

### macOS notes

The `curl` install script and `pip install` both work, and the TUI renders correctly in Terminal.app and iTerm2. However, **macOS does not support registering a custom URI scheme for a plain CLI tool**. The OS requires a proper `.app` bundle with a `CFBundleURLTypes` entry in `Info.plist` to handle `acc-connect://` links from the browser.

Until a bundled `.app` is provided, clicking **Connect** on a server browser website will do nothing on macOS. As a workaround, copy the `acc-connect://` URI from the browser and pass it manually:

```bash
acc-connector "acc-connect://hostname:9911?name=My+Server&persistent=true"
```

### Windows notes

The `curl` install script is bash-only. Use `pip install` directly instead:

```powershell
pip install git+https://github.com/cescofry/acc-connector-linux.git
```

Or, if you have the repository cloned:

```powershell
pip install .
```

[Windows Terminal](https://aka.ms/terminal) is recommended for the best TUI rendering experience. The built-in `cmd.exe` and older PowerShell consoles may not render the interface correctly.

**URI handler registration is not automatic on Windows.** The original [Windows ACC Connector](https://github.com/lonemeow/acc-connector) registers the `acc-connect://` scheme via its installer. This Python port does not currently write to the Windows registry. Until that is implemented, pass the URI manually:

```powershell
acc-connector "acc-connect://hostname:9911?name=My+Server&persistent=true"
```

### Config directory

On all platforms, configuration and logs are stored under `~/.config/acc-connector/` (i.e. `%USERPROFILE%\.config\acc-connector\` on Windows). This directory is created automatically on first run.

---



ACC's server browser discovers LAN servers by broadcasting a 6-byte UDP packet on port 8999. ACC Connector listens on that port, parses the request, and replies with the details of each configured server (name, IP, port). The game then lists those servers in its browser as if they were discovered natively on the network.

This is useful when ACC is running on a machine that cannot see the server by broadcast — for example when the server is on a different subnet, a VPN, or a remote host.

---

## Requirements

- Python 3.10 or later
- The `textual` library (see `requirements.txt`)

Install dependencies:

Install via curl (Linux/macOS — installs the `acc-connector` command globally):

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

## Finding servers

[acc-status.jonatan.net/servers](https://acc-status.jonatan.net/servers) is an alternative ACC server browser that lists public servers with car class, track, session info, and player counts. Each server has a **Connect** button that generates an `acc-connect://` URI and (on Linux with the handler registered) will launch ACC Connector automatically.

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
[ACC-Connector Windows Git Reposiory](https://github.com/lonemeow/acc-connector)

| Feature              | Windows version          | This (Linux/Python)                        |
|----------------------|--------------------------|--------------------------------------------|
| UI                   | Native GUI               | Terminal UI (via `textual`)                |
| URI handler          | Registered OS handler    | Registered via install script (Linux); CLI argument on macOS/Windows |
| Platform             | Windows only             | Linux, macOS, Windows (Python 3.10+)       |
| Config location      | Windows AppData          | `~/.config/acc-connector/` on all platforms |
| Discovery protocol   | Identical                | Identical                                  |
| URI format           | Identical                | Identical                                  |
