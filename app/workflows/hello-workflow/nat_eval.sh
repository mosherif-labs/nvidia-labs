#!/usr/bin/env bash
# Run nat eval inside WSL2: venv (Day 6) + keys from mosherif-labs/.env
set -euo pipefail
cd "$(dirname "$0")"
command -v uv >/dev/null || { echo "uv not installed in WSL: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
[ -d .venv ] || uv venv --python 3.12
source .venv/bin/activate
uv pip install -q "nvidia-nat[langchain,mcp,eval]"
set -a; source <(tr -d '\r' < ../../../../.env); set +a
nat eval --config_file config.yml --reps="${REPS:-3}"
