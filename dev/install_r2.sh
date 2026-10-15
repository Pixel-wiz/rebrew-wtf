set -e
cd /home/dev
[ -d radare2 ] || git clone -q --depth 1 https://github.com/radareorg/radare2
cd radare2 && ./sys/install.sh >/tmp/r2build.log 2>&1
export PATH=/usr/local/bin:$HOME/.local/bin:$PATH
radare2 -v 2>&1 | head -1
r2pm -U >/dev/null 2>&1 || true
r2pm -ci r2dec >/tmp/r2dec.log 2>&1 || tail -3 /tmp/r2dec.log
echo R2_READY
