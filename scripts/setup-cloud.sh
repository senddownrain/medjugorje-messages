#!/usr/bin/env bash
# Reproducible preparation for ephemeral cloud sessions (Claude Code, Codespaces, etc.).
# Run from any working directory. No credentials or database writes.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v node >/dev/null || { echo "ERROR: Node.js 22 or newer is required"; exit 1; }
command -v npm >/dev/null || { echo "ERROR: npm is required"; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: Python 3.12 is recommended"; exit 1; }

echo "[setup] Node: $(node --version); npm: $(npm --version); Python: $(python3 --version)"
npm install --no-audit --no-fund
python3 -m pip install -r requirements.txt
npm run check:data
python3 -m unittest discover -s tests -v
npm run build
echo "[setup] Cloud environment READY for code editing and private preview builds."
echo "[setup] For UI development: npm run dev; Vite port 5173."
