export PATH=/usr/local/bin:/home/dev/bin:/home/dev/.local/bin:$PATH
timeout 1500 r2pm -ci r2ghidra > /tmp/r2ghidra2.log 2>&1
echo "EXIT=$?"; tail -3 /tmp/r2ghidra2.log; echo DONE2
