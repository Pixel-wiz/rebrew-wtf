"""Blind room over a REAL public cloudflare tunnel: the host serves on localhost, cloudflared exposes a public
https://*.trycloudflare.com URL, and the guest joins THROUGH that public URL with a real httpx client. This is
the actual two-machine path end to end (minus only the second physical machine — the bytes traverse the internet
to cloudflare and back)."""
import re
import subprocess
import sys
import shutil
import threading
import time
from pathlib import Path

import uvicorn

from decompnet.app import collab
from decompnet.app.engine import RomNetwork

TOY = Path("/home/dev/targets/toy")
TOY_C = Path("/home/dev/targets/toy.c").read_text()
CLAMP_VA = 0x13a0
CF = str(Path.home() / "bin" / "cloudflared")


def slice_fn(text, name):
    m = re.search(rf"(^|\n)([A-Za-z_][\w \*]*\b{name}\s*\([^;]*?\)\s*\{{)", text)
    i = text.index("{", m.start(2)); depth = 0; j = i
    while j < len(text):
        depth += 1 if text[j] == "{" else -1 if text[j] == "}" else 0
        if depth == 0:
            return text[m.start(2):j + 1]
        j += 1


def main():
    ws = Path("/home/dev/tunnel-ws"); shutil.rmtree(ws, ignore_errors=True); ws.mkdir()
    port = 6801
    host = RomNetwork(ws / "host.db", ws / "host"); (ws / "host").mkdir(parents=True, exist_ok=True)
    slug = host.rebrew.import_binary(TOY, toolchain="gcc-14.2.0", confirmed=True, name="toy",
                                     blind=True, log=lambda *a: None)
    host.rooms[slug] = collab.Room(host, slug)
    code = host.rooms[slug].open_invite()
    server = uvicorn.Server(uvicorn.Config(collab.host_app(host, host.rooms), host="127.0.0.1",
                                           port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)

    # open a real quick tunnel and scrape the public URL from cloudflared's logs
    proc = subprocess.Popen([CF, "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"],
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
    print(f"public tunnel: {public}")
    if not public:
        proc.terminate(); server.should_exit = True
        print("\nTUNNEL FAIL: no public URL"); return 1
    try:
        time.sleep(3)  # let the edge register the tunnel
        guest = RomNetwork(ws / "guest.db", ws / "guest"); (ws / "guest").mkdir(parents=True, exist_ok=True)
        link = f"{public}/join/{code}#room={slug}"
        gslug = collab.join_room(guest, link, "remote", None, log=lambda *a: None, start=False)
        agent, _ = guest.local_agent("claude-1")
        want = f"fcn_{CLAMP_VA:08x}"
        guest.claim(agent, project=gslug, function=want)
        body = slice_fn(TOY_C, "toy_clamp").replace("toy_clamp", want)
        res = guest.attempt(agent, want, body, project=gslug)
        hs = host.store.one("SELECT status FROM functions f JOIN projects p ON p.id=f.project_id WHERE p.slug=? AND f.vram=?", slug, CLAMP_VA)
        gbytes = guest.store.one("SELECT SUM(LENGTH(target)) b FROM functions f JOIN projects p ON p.id=f.project_id WHERE p.slug=?", gslug)["b"] or 0
        ok = bool(res["matched"]) and bool(hs and hs["status"] == "matched") and gbytes == 0
        print(f"guest joined over the internet; attempt -> matched={res['matched']} score={res['score']}")
        print(f"host status={hs['status'] if hs else '?'}  guest target bytes={gbytes}")
        print(f"\nTUNNEL ROOM {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        proc.terminate(); server.should_exit = True


if __name__ == "__main__":
    sys.exit(main())
