"""Step-5 gate, in-process (no tunnel): a host shares a rebrew project; a guest joins, claims a specific
function, and matches it. Covers a NORMAL room (guest has the binary, works locally, host confirms) and a
BLIND room (guest has no binary; the host sends one function's asm on claim and judges every attempt)."""
import re
import sys
import shutil
from pathlib import Path

from starlette.testclient import TestClient

from decompnet.app import collab
from decompnet.app.engine import RomNetwork

BASE = "https://abc.trycloudflare.com"
TOY = Path("/home/dev/targets/toy")
TOY_C = Path("/home/dev/targets/toy.c").read_text()
CLAMP_VA = 0x13a0  # toy_clamp


def slice_fn(text, name):
    m = re.search(rf"(^|\n)([A-Za-z_][\w \*]*\b{name}\s*\([^;]*?\)\s*\{{)", text)
    i = text.index("{", m.start(2)); depth = 0; j = i
    while j < len(text):
        depth += 1 if text[j] == "{" else -1 if text[j] == "}" else 0
        if depth == 0:
            return text[m.start(2):j + 1]
        j += 1


def host_room(ws, blind):
    host = RomNetwork(ws / "host.db", ws / "host"); (ws / "host").mkdir(parents=True, exist_ok=True)
    slug = host.rebrew.import_binary(TOY, toolchain="gcc-14.2.0", confirmed=True, name="toy",
                                     blind=blind, log=lambda *a: None)
    host.rooms[slug] = collab.Room(host, slug)
    code = host.rooms[slug].open_invite()
    client = TestClient(collab.host_app(host, host.rooms), base_url=BASE)
    return host, slug, client, f"{BASE}/join/{code}#room={slug}"


def run(ws, blind):
    host, slug, client, link = host_room(ws, blind)
    guest = RomNetwork(ws / "guest.db", ws / "guest"); (ws / "guest").mkdir(parents=True, exist_ok=True)
    binary = None if blind else TOY.read_bytes()
    gslug = collab.join_room(guest, link, "alex", binary, log=lambda *a: None, client=client, start=False)
    agent, _ = guest.local_agent("claude-1")

    # name the member works under: real name in a normal room, opaque fcn_<va> in a blind room
    want = f"fcn_{CLAMP_VA:08x}" if blind else "toy_clamp"
    claim = guest.claim(agent, project=gslug, function=want)
    body = slice_fn(TOY_C, "toy_clamp").replace("toy_clamp", want)
    res = guest.attempt(agent, want, body, project=gslug)

    label = "BLIND " if blind else "normal"
    print(f"[{label}] claim '{want}': {claim.splitlines()[0][:48]}")
    print(f"[{label}] attempt -> matched={res['matched']} score={res['score']} :: {res['text'].splitlines()[0][:48]}")

    ok = bool(res["matched"])
    hs = host.store.one("SELECT status FROM functions f JOIN projects p ON p.id=f.project_id "
                        "WHERE p.slug=? AND f.vram=?", slug, CLAMP_VA)
    print(f"[{label}] host recorded status: {hs['status'] if hs else '?'} (expect matched)")
    ok &= bool(hs and hs["status"] == "matched")

    if blind:  # the guest must hold NO target bytes and no scope
        gtotal = guest.store.one("SELECT COUNT(*) c FROM functions f JOIN projects p ON p.id=f.project_id WHERE p.slug=?", gslug)["c"]
        gbytes = guest.store.one("SELECT SUM(LENGTH(target)) b FROM functions f JOIN projects p ON p.id=f.project_id WHERE p.slug=?", gslug)["b"] or 0
        print(f"[BLIND ] guest holds {gtotal} function(s), {gbytes} target bytes (expect 1, 0 — no binary, no scope)")
        ok &= gtotal == 1 and gbytes == 0
    return ok


def main():
    ok = True
    ws1 = Path("/home/dev/room-normal"); shutil.rmtree(ws1, ignore_errors=True); ws1.mkdir()
    ok &= run(ws1, False)
    print()
    ws2 = Path("/home/dev/room-blind"); shutil.rmtree(ws2, ignore_errors=True); ws2.mkdir()
    ok &= run(ws2, True)
    print(f"\nROOMS {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
