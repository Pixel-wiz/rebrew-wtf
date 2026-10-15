cd /mnt/c/debug/rebrew-wtf
export REBREW_TOOLCHAINS_DIR=/home/dev/recompile-toolchains PATH=/home/dev/.local/bin:$PATH
/home/dev/fork-venv/bin/python -m pytest -q -p no:cacheprovider -rfE 2>&1 | grep -E "^(FAILED|ERROR)" | head -30
echo "--- one error detail ---"
/home/dev/fork-venv/bin/python -m pytest -q -p no:cacheprovider tests/test_network.py::test_export 2>&1 | grep -iE "error|git|not found|No such|command" | head -6
