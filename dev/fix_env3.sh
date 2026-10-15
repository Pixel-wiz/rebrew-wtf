set -e
cd /mnt/c/debug/rebrew-wtf
export UV_LINK_MODE=copy PATH=/home/dev/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/home/dev/fork-venv UV_PYTHON=3.13
rm -rf /home/dev/fork-venv
uv sync --frozen --all-extras -q --python 3.13 2>&1 | tail -2
/home/dev/fork-venv/bin/python --version
VIRTUAL_ENV=/home/dev/fork-venv uv pip install -q "rebrew @ git+https://github.com/maci0/rebrew.git" 2>&1 | tail -2
/home/dev/fork-venv/bin/python -c 'import decompnet, rebrew, numpy, lief; print("imports OK; numpy", numpy.__version__)'
