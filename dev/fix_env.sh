set -e
SP=$(ls -d /home/dev/fork-venv/lib/python3*/site-packages)
rm -f "$SP/_rebrew.pth"
/home/dev/fork-venv/bin/python --version
export UV_LINK_MODE=copy PATH=/home/dev/.local/bin:$PATH
# install rebrew INTO the fork venv so numpy/lief match this interpreter
VIRTUAL_ENV=/home/dev/fork-venv uv pip install -q "rebrew @ git+https://github.com/maci0/rebrew.git" 2>&1 | tail -3
/home/dev/fork-venv/bin/python -c 'import decompnet, rebrew, numpy, lief; print("OK", rebrew.__version__ if hasattr(rebrew,"__version__") else "rebrew", "numpy", numpy.__version__)'
