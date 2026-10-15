"""Live two-process session, guest side: a SEPARATE process and identity. Reads the host's public invite link,
joins the blind room over the real internet, claims a function, and matches it — the host (other process) judges.
Confirms a genuine second-member session end to end."""
import json
import re
import sys
import time
from pathlib import Path

from decompnet.app import collab
from decompnet.app.engine import RomNetwork

TOY_C = Path("/home/dev/targets/toy.c").read_text()
LINKFILE = Path("/home/dev/live-link.json")


def slice_fn(text, name):
    m = re.search(rf"(^|\n)([A-Za-z_][\w \*]*\b{name}\s*\([^;]*?\)\s*\{{)", text)
    i = text.index("{", m.start(2)); depth = 0; j = i
    while j < len(text):
        depth += 1 if text[j] == "{" else -1 if text[j] == "}" else 0
        if depth == 0:
            return text[m.start(2):j + 1]
        j += 1


def main():
    for _ in range(120):  # wait for the host process to publish the link
        if LINKFILE.exists():
            break
        time.sleep(0.5)
    if not LINKFILE.exists():
        print("GUEST: host link never appeared"); return 1
    link = json.loads(LINKFILE.read_text())["link"]
    print(f"GUEST: joining {link.split('/join')[0]} as an independent member")
    ws = Path("/home/dev/live-guest")
    import shutil; shutil.rmtree(ws, ignore_errors=True); ws.mkdir(parents=True)
    guest = RomNetwork(ws / "guest.db", ws)
    gslug = collab.join_room(guest, link, "teammate", None, log=lambda *a: None, start=False)
    agent, _ = guest.local_agent("teammate-agent")
    want = "fcn_000013a0"
    guest.claim(agent, project=gslug, function=want)
    body = slice_fn(TOY_C, "toy_clamp").replace("toy_clamp", want)
    res = guest.attempt(agent, want, body, project=gslug)
    gbytes = guest.store.one("SELECT SUM(LENGTH(target)) b FROM functions f JOIN projects p ON p.id=f.project_id WHERE p.slug=?", gslug)["b"] or 0
    print(f"GUEST: matched={res['matched']} score={res['score']} target-bytes-held={gbytes}")
    Path("/home/dev/live-done").write_text("1")
    return 0 if res["matched"] and gbytes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
