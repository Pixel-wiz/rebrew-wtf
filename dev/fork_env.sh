set -e
cd /mnt/c/debug/rebrew-wtf
export UV_PROJECT_ENVIRONMENT=/home/dev/fork-venv UV_LINK_MODE=copy PATH=/home/dev/.local/bin:$PATH
uv sync --frozen --all-extras -q 2>&1 | tail -2
# rebrew lives in its own uv tool env; expose it to the fork venv via a .pth
REBREW_SP=$(ls -d /home/dev/.local/share/uv/tools/rebrew/lib/python3*/site-packages)
echo "$REBREW_SP" > "$(ls -d /home/dev/fork-venv/lib/python3*/site-packages)/_rebrew.pth"
/home/dev/fork-venv/bin/python -c 'import decompnet, rebrew, lief; print("decompnet+rebrew import OK; lief", lief.__version__)'
