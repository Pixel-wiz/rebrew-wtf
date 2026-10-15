export PATH=/usr/local/bin:/home/dev/bin:/home/dev/.local/bin:$PATH
timeout 1500 r2pm -ci r2ghidra > /tmp/r2ghidra.log 2>&1
echo "EXIT=$?"
tail -4 /tmp/r2ghidra.log
echo R2GHIDRA_DONE
