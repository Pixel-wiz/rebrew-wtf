"""Live SF64 second-member session, guest side: a separate process + identity joins the host's Star Fox 64 room
over the real cloudflare tunnel with its own copy of the ROM, claims the open function, and submits the known-
good C. The host judges with IDO 5.3 and confirms a byte match — a genuine live second-member match on SF64."""
import json, sys, time
from pathlib import Path
from decompnet.app import collab
from decompnet.app.engine import RomNetwork

LINK = Path("/home/decomp/sf-live-link.json")
SRC = json.loads(Path("/home/decomp/sf-func.json").read_text())  # {name, source, flags}


def main():
    for _ in range(240):
        if LINK.exists(): break
        time.sleep(0.5)
    if not LINK.exists():
        print("SF-GUEST: host link never appeared"); return 1
    info = json.loads(LINK.read_text()); link = info["link"]
    print(f"SF-GUEST: joining Star Fox 64 room at {link.split('/join')[0]} (own ROM copy, own identity)")
    g = Path("/home/decomp/sf-guest"); import shutil; shutil.rmtree(g, ignore_errors=True); (g / ".decomp").mkdir(parents=True)
    guest = RomNetwork(g / ".decomp" / "decomp.db", g)
    rom = Path("/home/decomp/Decomp/starfox64/rom.z64")
    gslug = collab.join_room(guest, link, "nightbuild", rom, log=lambda *a: None, start=False)
    agent, _ = guest.local_agent("nightbuild-agent")
    guest.claim(agent, project=gslug, function=SRC["name"])
    res = guest.attempt(agent, SRC["name"], SRC["source"], project=gslug)
    print(f"SF-GUEST: {SRC['name']} matched={res['matched']} score={res['score']} :: {res['text'].splitlines()[0][:48]}")
    Path("/home/decomp/sf-live-done").write_text("1")
    return 0 if res["matched"] else 1


if __name__ == "__main__":
    sys.exit(main())
