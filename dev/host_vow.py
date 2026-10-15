"""Host a BLIND rebrew room for two_ring_vow.exe over a real cloudflare tunnel, and serve+judge until stopped.
The exe is stripped, so functions are recovered via Ghidra (the engine's new discovery fallback). Writes the
public invite link to /home/dev/vow-link.txt and stays alive (host holds the binary; members join with nothing)."""
import re
import subprocess
import threading
import time
from pathlib import Path

import uvicorn
from decompnet.app import collab
from decompnet.app.engine import RomNetwork

WS = Path("/home/dev/vow-host")
PORT = 6834
CF = str(Path.home() / "bin" / "cloudflared")
EXE = Path("/mnt/c/Users/Todd/Downloads/6acfedfb6349e4b2540c7170/two_ring_vow.exe")
LINKFILE = Path("/home/dev/vow-link.txt")
STOP = Path("/home/dev/vow-stop")


def main():
    import shutil
    shutil.rmtree(WS, ignore_errors=True); WS.mkdir(parents=True)
    LINKFILE.unlink(missing_ok=True); STOP.unlink(missing_ok=True)
    host = RomNetwork(WS / "host.db", WS)
    print("importing (stripped → Ghidra discovery, ~1-2 min)...", flush=True)
    slug = host.rebrew.import_binary(EXE, toolchain="gcc-14.2.0", confirmed=True,
                                     name="two_ring_vow", blind=True, log=lambda *a: print(*a, flush=True))
    n = host.store.one("SELECT COUNT(*) c FROM functions f JOIN projects p ON p.id=f.project_id WHERE p.slug=?", slug)["c"]
    print(f"project {slug}: {n} functions (blind)", flush=True)
    host.rooms[slug] = collab.Room(host, slug)
    code = host.rooms[slug].open_invite()
    server = uvicorn.Server(uvicorn.Config(collab.host_app(host, host.rooms), host="127.0.0.1", port=PORT, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    proc = subprocess.Popen([CF, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{PORT}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    public, t0 = None, time.time()
    while time.time() - t0 < 60:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.1); continue
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
        if m:
            public = m.group(0); break
    if not public:
        print("no tunnel", flush=True); proc.terminate(); return 1
    time.sleep(8)  # let the edge propagate
    link = f"{public}/join/{code}#room={slug}"
    LINKFILE.write_text(link)
    print(f"INVITE: {link}", flush=True)
    print("serving — teammate joins with NO file. Create /home/dev/vow-stop to shut down.", flush=True)
    while not STOP.exists():
        time.sleep(1)
    proc.terminate(); server.should_exit = True
    print("stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
