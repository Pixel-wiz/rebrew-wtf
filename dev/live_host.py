"""Live two-process session, host side: import a blind rebrew project, open a REAL cloudflare tunnel, and serve
until told to stop. Writes the public invite link to a file the separate guest process reads. This is a genuine
independent host — its own process, DB, and public URL on the internet."""
import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import uvicorn
from decompnet.app import collab
from decompnet.app.engine import RomNetwork

WS = Path("/home/dev/live-host"); PORT = 6833
CF = str(Path.home() / "bin" / "cloudflared")
LINKFILE = Path("/home/dev/live-link.json")


def main():
    import shutil
    shutil.rmtree(WS, ignore_errors=True); WS.mkdir(parents=True)
    LINKFILE.unlink(missing_ok=True)
    host = RomNetwork(WS / "host.db", WS)
    slug = host.rebrew.import_binary(Path("/home/dev/targets/toy"), toolchain="gcc-14.2.0",
                                     confirmed=True, name="toy", blind=True, log=lambda *a: None)
    host.rooms[slug] = collab.Room(host, slug)
    code = host.rooms[slug].open_invite()
    server = uvicorn.Server(uvicorn.Config(collab.host_app(host, host.rooms), host="127.0.0.1", port=PORT, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    proc = subprocess.Popen([CF, "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--no-autoupdate"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    public = None
    t0 = time.time()
    while time.time() - t0 < 60:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.1); continue
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
        if m:
            public = m.group(0); break
    if not public:
        print("HOST: no tunnel"); proc.terminate(); return 1
    LINKFILE.write_text(json.dumps({"link": f"{public}/join/{code}#room={slug}", "slug": slug}))
    print(f"HOST: serving {public} room {slug} (vram 0x13a0 available to claim)")
    # serve until the guest signals done (writes live-done) or 5 min
    for _ in range(600):
        if Path("/home/dev/live-done").exists():
            break
        time.sleep(0.5)
    m = host.store.one("SELECT status FROM functions f JOIN projects p ON p.id=f.project_id WHERE p.slug=? AND f.vram=?", slug, 0x13a0)
    members = len(host.rooms[slug].members())
    print(f"HOST: members={members} func_0x13a0 status={m['status'] if m else '?'}")
    proc.terminate(); server.should_exit = True
    return 0


if __name__ == "__main__":
    sys.exit(main())
