export REBREW_TOOLCHAINS_DIR=~/recompile-toolchains PATH=$HOME/.local/bin:$PATH
rebrew intake --help 2>&1 | sed -n 1,50p
echo ===NM===
~/.local/share/uv/tools/rebrew/bin/python - <<'PY'
import subprocess
out = subprocess.run(["readelf","-sW","/home/dev/targets/toy"],capture_output=True,text=True).stdout
for l in out.splitlines():
    p=l.split()
    if len(p)>=8 and p[3]=="FUNC" and p[7].startswith("toy_"):
        print(p[7], "va=0x"+p[1], "size="+p[2])
PY
