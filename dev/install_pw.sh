export PATH=/home/dev/.local/bin:$PATH VIRTUAL_ENV=/home/dev/fork-venv
uv pip install -q playwright 2>&1 | tail -2
/home/dev/fork-venv/bin/python -m playwright install chromium 2>&1 | tail -3
/home/dev/fork-venv/bin/python -m playwright install-deps chromium 2>&1 | tail -2 || true
echo PW_READY
