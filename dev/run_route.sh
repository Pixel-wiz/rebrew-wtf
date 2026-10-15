cd /mnt/c/debug/rebrew-wtf
export REBREW_TOOLCHAINS_DIR=/home/dev/recompile-toolchains PATH=/home/dev/.local/bin:$PATH
/home/dev/fork-venv/bin/python -m pytest -q -p no:cacheprovider tests/test_rebrew_import_route.py 2>&1 | tail -6
