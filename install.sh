#!/usr/bin/env bash
set -euo pipefail

python3 -c "import sys; assert sys.version_info >= (3,10), 'x'" 2>/dev/null || {
    echo "Error: Python 3.10 or later is required."
    exit 1
}

pip install git+https://github.com/cescofry/acc-connector-linux.git

echo ""
echo "Done! Run 'acc-connector' to start."
