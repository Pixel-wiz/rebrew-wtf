cd /mnt/c/debug/rebrew-wtf
export REBREW_TOOLCHAINS_DIR=/home/dev/recompile-toolchains PATH=/home/dev/.local/bin:$PATH
/home/dev/fork-venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -8
