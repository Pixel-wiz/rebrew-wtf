set -e
cd /mnt/c/debug/rebrew-wtf
export UV_PROJECT_ENVIRONMENT=$HOME/rebrew-wtf-venv UV_LINK_MODE=copy
~/.local/bin/uv sync --frozen --all-extras -q 2>&1 | tail -3
~/.local/bin/uv run --frozen python -m pytest -q -p no:cacheprovider "$@" 2>&1 | tail -25
