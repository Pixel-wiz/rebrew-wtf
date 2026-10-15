#!/bin/bash
# Wait for the gcc-14.2.0 image build to finish, then run the known-answer bridge self-test.
export REBREW_TOOLCHAINS_DIR=/home/dev/recompile-toolchains PATH=/home/dev/.local/bin:/usr/bin:/bin
PY=/home/dev/.local/share/uv/tools/rebrew/bin/python
for i in $(seq 1 240); do   # up to ~4h
  if docker images --format '{{.Repository}}:{{.Tag}}' | grep -q '^rebrew/gcc:14'; then
    echo "=== gcc image ready after ${i} checks ($(date -u +%H:%M:%S)) ==="
    $PY /mnt/c/debug/rebrew-wtf/dev/rebrew_bridge.py /home/dev/proj-toy /home/dev/targets/toy.c
    echo "SELFTEST_EXIT=$?"
    exit 0
  fi
  if ! systemctl is-active --quiet rebrew-tc-gcc14b && ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -q '^rebrew/gcc:14'; then
    echo "=== build unit stopped without producing image at check ${i}; tail: ==="
    tail -c 500 /home/dev/tc-gcc14.log
    exit 1
  fi
  sleep 60
done
echo "=== timed out waiting for gcc image ==="; exit 1
