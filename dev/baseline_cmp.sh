cd /mnt/c/debug/rebrew-wtf
export REBREW_TOOLCHAINS_DIR=/home/dev/recompile-toolchains PATH=/home/dev/.local/bin:$PATH
echo "=== WITH my changes ==="
/home/dev/fork-venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -1
git stash push -- src/decompnet/app/engine.py >/dev/null 2>&1 && echo "(engine.py stashed)"
echo "=== baseline (engine.py reverted) ==="
/home/dev/fork-venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -1
git stash pop >/dev/null 2>&1 && echo "(restored)"
