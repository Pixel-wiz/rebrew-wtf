export REBREW_TOOLCHAINS_DIR=/home/dev/recompile-toolchains PATH=/home/dev/.local/bin:/usr/bin:/bin
cd /home/dev/proj-toy
cat > /tmp/clamp.c <<'C'
int toy_clamp(int v, int lo, int hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}
C
# compile with the rebrew gcc image the same way rebrew does
docker run --rm -v /tmp:/w -w /w rebrew/gcc:14.2.0-linux-x64 gcc -O2 -c clamp.c -o clamp.o 2>&1 | tail -3
echo "=== symbols in clamp.o ==="
nm /tmp/clamp.o 2>&1
echo "=== readelf ==="
readelf -sW /tmp/clamp.o 2>&1 | grep -i toy_clamp
