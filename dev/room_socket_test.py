"""Step-5 over a REAL HTTP socket (not in-process TestClient): the host serves the collab app with uvicorn on
127.0.0.1:<port>; the guest joins over real HTTP with a real httpx client. This exercises the actual network
transport (JSON over sockets) a tunnel would carry — the tunnel itself only adds NAT traversal, not new code."""
import re
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


def slice_fn(text, name):
    m = re.search(rf"(^|\n)([A-Za-z_][\w \*]*\b{name}\s*\([^;]*?\)\s*\{{)", text)
    i = text.index("{", m.start(2)); depth = 0; j = i
    while j < len(text):
        depth += 1 if text[j] == "{" else -1 if text[j] == "}" else 0
        if depth == 0:
            return text[m.start(2):j + 1]
        j += 1


def main():
    ws = Path("/home/dev/room-socket"); shutil.rmtree(ws, ignore_errors=True); ws.mkdir()
    port = 6799
    host = RomNetwork(ws / "host.db", ws / "host"); (ws / "host").mkdir(parents=True, exist_ok=True)
    slug = host.rebrew.import_binary(TOY, toolchain="gcc-14.2.0", confirmed=True, name="toy",
                                     blind=True, log=lambda *a: None)
    host.rooms[slug] = collab.Room(host, slug)
    code = host.rooms[slug].open_invite()

    server = uvicorn.Server(uvicorn.Config(collab.host_app(host, host.rooms), host="127.0.0.1",
                                           port=port, log_level="error"))
    t = threading.Thread(target=server.run, daemon=True); t.start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    print(f"host serving on 127.0.0.1:{port}, started={server.started}")

    try:
        guest = RomNetwork(ws / "guest.db", ws / "guest"); (ws / "guest").mkdir(parents=True, exist_ok=True)
        link = f"http://127.0.0.1:{port}/join/{code}#room={slug}"
        # no client= → join_room uses a REAL httpx.Client over the socket
        gslug = collab.join_room(guest, link, "alex", None, log=lambda *a: None, start=False)
        agent, _ = guest.local_agent("claude-1")
        want = f"fcn_{CLAMP_VA:08x}"
        claim = guest.claim(agent, project=gslug, function=want)
        body = slice_fn(TOY_C, "toy_clamp").replace("toy_clamp", want)
        res = guest.attempt(agent, want, body, project=gslug)
        print(f"claim: {claim.splitlines()[0][:50]}")
        print(f"attempt over real HTTP -> matched={res['matched']} score={res['score']} :: {res['text'].splitlines()[0][:40]}")
        hs = host.store.one("SELECT status FROM functions f JOIN projects p ON p.id=f.project_id WHERE p.slug=? AND f.vram=?", slug, CLAMP_VA)
        gbytes = guest.store.one("SELECT SUM(LENGTH(target)) b FROM functions f JOIN projects p ON p.id=f.project_id WHERE p.slug=?", gslug)["b"] or 0
        ok = bool(res["matched"]) and bool(hs and hs["status"] == "matched") and gbytes == 0
        print(f"host status={hs['status'] if hs else '?'}  guest target bytes={gbytes}")
        print(f"\nREAL-SOCKET ROOM {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        server.should_exit = True
        t.join(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
