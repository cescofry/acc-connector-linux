#!/usr/bin/env bash
set -euo pipefail

python3 -c "import sys; assert sys.version_info >= (3,10), 'x'" 2>/dev/null || {
    echo "Error: Python 3.10 or later is required."
    exit 1
}

pip install git+https://github.com/cescofry/acc-connector-linux.git

# Register the acc-connect:// URI scheme handler on Linux via xdg-mime
if [[ "$(uname -s)" == "Linux" ]]; then
    DESKTOP_DIR="${HOME}/.local/share/applications"
    DESKTOP_FILE="${DESKTOP_DIR}/acc-connector.desktop"
    ACC_CONNECTOR_BIN="$(command -v acc-connector)"

    mkdir -p "${DESKTOP_DIR}"

    cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Type=Application
Name=ACC Connector
Exec=${ACC_CONNECTOR_BIN} %u
MimeType=x-scheme-handler/acc-connect;
NoDisplay=true
EOF

    xdg-mime default acc-connector.desktop x-scheme-handler/acc-connect
    update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true

    echo ""
    echo "Registered acc-connect:// URI handler."
fi

echo ""
echo "Done! Run 'acc-connector' to start."
