export PATH=$HOME/bin:$HOME/.local/bin:$PATH REBREW_TOOLCHAINS_DIR=$HOME/.local/share/decompnet/toolchains
PY=$(ls /home/decomp/.local/share/uv/tools/decompnet/bin/python)
$PY /mnt/c/debug/rebrew-wtf/dev/sf_live_guest.py
echo "SF_GUEST_EXIT=$?"
